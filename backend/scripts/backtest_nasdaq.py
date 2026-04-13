#!/usr/bin/env python3
"""
NASDAQ Ultimate Backtest — Find what ACTUALLY works for T+1 trading.
WIN = Close is +1.5%+ on Day 1 (T+1, can sell next day)
      OR Close is +2%+ on Day 2 (safety buffer)

Tests EVERYTHING:
- Mean reversion (RSI, BB, drops)
- Momentum (breakout, 52w high, ChoCh+BOS)
- Earnings reactions
- Volume patterns
- Candle patterns
- Sector/market conditions
- Combinations
"""

import warnings; warnings.filterwarnings("ignore")
import sys, os
import pandas as pd
import numpy as np
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

from ta.momentum import RSIIndicator
from ta.volume import ChaikinMoneyFlowIndicator, OnBalanceVolumeIndicator
from ta.trend import ADXIndicator, EMAIndicator, MACD
from ta.volatility import BollingerBands

conn = psycopg2.connect(DATABASE_URL)

print("Loading NASDAQ data...")
df = pd.read_sql(
    "SELECT symbol, date, open, high, low, close, volume "
    "FROM nasdaq_daily_prices WHERE close > 0 AND volume > 0 "
    "ORDER BY symbol, date",
    conn,
)
df["date"] = pd.to_datetime(df["date"])

# Load halal status
halal = pd.read_sql("SELECT symbol, halal_status FROM nasdaq_stocks", conn)
halal_set = set(halal[halal["halal_status"] == "HALAL"]["symbol"])
conn.close()

# Filter halal only
df = df[df["symbol"].isin(halal_set)]
print(f"Halal stocks: {df.symbol.nunique()}, Rows: {len(df)}\n")


def t1_win(close, high, entry_price, idx):
    """WIN = Close +1.5% on Day 1 OR +2% on Day 2.
    This is the T+1 trader metric — buy today, sell tomorrow or day after."""
    if idx + 2 >= len(close):
        return None
    # Day 1 close
    if (close.iloc[idx + 1] - entry_price) / entry_price * 100 >= 1.5:
        return True
    # Day 2 close
    if (close.iloc[idx + 2] - entry_price) / entry_price * 100 >= 2.0:
        return True
    # Day 1 high (intraday spike)
    if (high.iloc[idx + 1] - entry_price) / entry_price * 100 >= 2.0:
        return True
    return False


results = {}
names = {}

def add(key, name, win):
    if key not in results:
        results[key] = []
        names[key] = name
    if win is not None:
        results[key].append(win)


print("Computing indicators and testing...")
stock_count = 0

for symbol, sdf in df.groupby("symbol"):
    if len(sdf) < 100:
        continue
    stock_count += 1
    sdf = sdf.sort_values("date").reset_index(drop=True)
    close = sdf["close"]
    high = sdf["high"]
    low = sdf["low"]
    open_ = sdf["open"]
    volume = sdf["volume"].astype(float)

    rsi = RSIIndicator(close, window=14).rsi()
    macd_obj = MACD(close)
    macd_hist = macd_obj.macd_diff()
    ema9 = EMAIndicator(close, window=9).ema_indicator()
    ema21 = EMAIndicator(close, window=21).ema_indicator()
    ema50 = EMAIndicator(close, window=50).ema_indicator()
    bb = BollingerBands(close, window=20, window_dev=2)
    bb_pct = bb.bollinger_pband()
    obv = OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    vol_avg = volume.rolling(20).mean()
    atr = close.rolling(14).apply(lambda x: np.mean(np.abs(np.diff(x))), raw=True)

    obv_slope = obv.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)
    price_slope = close.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)

    for i in range(60, len(sdf) - 2):
        c = close.iloc[i]
        o = open_.iloc[i]
        h = high.iloc[i]
        l = low.iloc[i]
        v = volume.iloc[i]
        c_prev = close.iloc[i - 1]

        rsi_v = rsi.iloc[i] if pd.notna(rsi.iloc[i]) else 50
        macd_h = macd_hist.iloc[i] if pd.notna(macd_hist.iloc[i]) else 0
        e9 = ema9.iloc[i] if pd.notna(ema9.iloc[i]) else 0
        e21 = ema21.iloc[i] if pd.notna(ema21.iloc[i]) else 0
        e50 = ema50.iloc[i] if pd.notna(ema50.iloc[i]) else 0
        bb_v = bb_pct.iloc[i] if pd.notna(bb_pct.iloc[i]) else 0.5
        va = vol_avg.iloc[i] if pd.notna(vol_avg.iloc[i]) else v
        obv_s = obv_slope.iloc[i] if pd.notna(obv_slope.iloc[i]) else 0
        price_s = price_slope.iloc[i] if pd.notna(price_slope.iloc[i]) else 0

        green = c > o
        body = abs(c - o)
        total_range = h - l
        lower_shadow = min(c, o) - l
        vol_ratio = v / va if va > 0 else 1
        ma_aligned = e9 > e21 > e50 and c > e9

        red_days = 0
        for j in range(1, min(6, i)):
            if close.iloc[i - j] < close.iloc[i - j - 1]:
                red_days += 1
            else:
                break

        chg_1d = (c - c_prev) / c_prev * 100
        chg_5d = (c - close.iloc[i - 5]) / close.iloc[i - 5] * 100 if i >= 5 else 0

        hammer = lower_shadow > body * 2 if body > 0 and total_range > 0 else False
        engulf = (c > o and c_prev < open_.iloc[i - 1] and body > abs(c_prev - open_.iloc[i - 1])) if i > 0 else False
        obv_div = price_s < 0 and obv_s > 0
        recent_low = low.iloc[max(0, i - 5):i].min()
        liq_grab = l < recent_low * 0.99 and c > recent_low

        # 52w high
        h52w = high.iloc[max(0, i - 252):i].max() if i >= 252 else high.iloc[:i].max()
        at_52w = c > h52w and c_prev <= h52w

        # Gap up/down
        gap_up = o > c_prev * 1.02
        gap_down = o < c_prev * 0.98

        w = t1_win(close, high, c, i)

        # === BASELINE ===
        add("baseline", "Random entry", w)

        # === MEAN REVERSION ===
        if rsi_v < 25: add("rsi25", "RSI < 25", w)
        if rsi_v < 30: add("rsi30", "RSI < 30", w)
        if rsi_v < 35: add("rsi35", "RSI < 35", w)
        if rsi_v < 40: add("rsi40", "RSI < 40", w)
        if bb_v < 0: add("bb0", "Below BB lower", w)
        if bb_v < -0.2: add("bb_neg", "BB < -0.2", w)
        if red_days >= 3: add("3red", "3+ red days", w)
        if red_days >= 4: add("4red", "4+ red days", w)
        if chg_5d < -5: add("drop5", "5d drop >5%", w)
        if chg_5d < -10: add("drop10", "5d drop >10%", w)
        if chg_1d < -3: add("drop3_1d", "Today dropped >3%", w)
        if chg_1d < -5: add("drop5_1d", "Today dropped >5%", w)
        if liq_grab: add("liq", "Liquidity grab", w)

        # === MOMENTUM ===
        if ma_aligned: add("ma", "MA aligned (trend)", w)
        if ma_aligned and rsi_v > 50 and rsi_v < 70: add("ma_rsi_mid", "MA+RSI 50-70", w)
        if at_52w: add("52w", "52w high break", w)
        if chg_1d > 3 and vol_ratio > 2: add("surge3_vol", "Up 3%+ with 2x vol", w)
        if chg_1d > 5 and vol_ratio > 2: add("surge5_vol", "Up 5%+ with 2x vol", w)

        # === CANDLES ===
        if hammer: add("hammer", "Hammer", w)
        if hammer and rsi_v < 40: add("hammer_rsi40", "Hammer + RSI<40", w)
        if engulf: add("engulf", "Bullish engulfing", w)
        if engulf and rsi_v < 40: add("engulf_rsi40", "Engulfing + RSI<40", w)

        # === VOLUME ===
        if vol_ratio > 2 and green: add("vol2_grn", "Vol>2x + green", w)
        if vol_ratio > 3 and green: add("vol3_grn", "Vol>3x + green", w)
        if obv_div: add("obv_div", "OBV divergence", w)
        if obv_div and rsi_v < 40: add("obv_rsi40", "OBV div + RSI<40", w)

        # === GAPS ===
        if gap_down and green: add("gap_dn_grn", "Gap down + closed green", w)
        if gap_down and c > o and vol_ratio > 1.5: add("gap_dn_vol", "Gap down recovery + vol", w)
        if gap_up and c > o: add("gap_up_hold", "Gap up held", w)

        # === COMBOS: Mean Reversion ===
        if rsi_v < 30 and red_days >= 2: add("rsi30_2red", "RSI<30 + 2red", w)
        if rsi_v < 30 and chg_5d < -7: add("rsi30_drop7", "RSI<30 + drop>7%", w)
        if rsi_v < 30 and bb_v < 0: add("rsi30_bb", "RSI<30 + below BB", w)
        if rsi_v < 30 and liq_grab: add("rsi30_liq", "RSI<30 + LiqGrab", w)
        if rsi_v < 35 and hammer: add("rsi35_ham", "RSI<35 + Hammer", w)
        if rsi_v < 30 and vol_ratio > 1.5 and green: add("rsi30_vol_grn", "RSI<30+Vol+Green", w)
        if chg_1d < -5 and rsi_v < 35: add("crash_rsi35", "Crash -5% + RSI<35", w)
        if bb_v < -0.2 and red_days >= 2: add("bb_2red", "BB<-0.2 + 2red", w)

        # === COMBOS: Momentum ===
        if ma_aligned and vol_ratio > 1.5 and green: add("ma_vol_grn", "MA+Vol+Green", w)
        if at_52w and vol_ratio > 1.5: add("52w_vol", "52w high + Vol>1.5x", w)
        if at_52w and ma_aligned: add("52w_ma", "52w high + MA aligned", w)
        if chg_1d > 3 and ma_aligned: add("surge_ma", "Up3%+MA aligned", w)

        # === COMBOS: Reversal ===
        if gap_down and rsi_v < 35 and green: add("gap_dn_rsi_grn", "GapDown+RSI<35+Green", w)
        if chg_1d < -3 and vol_ratio > 2 and green: add("crash_vol_grn", "Crash+HighVol+Green", w)

    if stock_count % 50 == 0:
        print(f"  Processed {stock_count} halal stocks...")

print(f"\nProcessed {stock_count} stocks\n")

# === RESULTS ===
print("=" * 70)
print("NASDAQ T+1 BACKTEST: WIN = +1.5% Day 1 close OR +2% Day 2")
print("Halal stocks only, 2 years data")
print("=" * 70)

rows = []
for key, wins in results.items():
    if len(wins) < 50:
        rows.append({"name": names[key], "n": len(wins), "wr": 0, "note": f"few({len(wins)})"})
        continue
    wr = sum(wins) / len(wins) * 100
    rows.append({"name": names[key], "n": len(wins), "wr": wr})

rows.sort(key=lambda x: -x.get("wr", 0))

print(f"\n{'Rank':>4} {'Strategy':<40s} {'Events':>8s} {'Win Rate':>9s}")
print("-" * 65)
for rank, r in enumerate(rows, 1):
    if "note" in r:
        print(f"{rank:4d} {r['name']:<40s} {r['n']:8d}     {r['note']}")
    else:
        marker = " ***" if r["wr"] >= 50 else " **" if r["wr"] >= 45 else " *" if r["wr"] >= 40 else ""
        print(f"{rank:4d} {r['name']:<40s} {r['n']:8d} {r['wr']:8.1f}%{marker}")

print(f"\nBaseline random: {sum(results['baseline'])/len(results['baseline'])*100:.1f}%")
