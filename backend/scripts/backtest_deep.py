#!/usr/bin/env python3
"""
NASDAQ Deep Backtest — MACD, Fibonacci, Breakouts, ICT, everything.
WIN = Close +1.5% Day 1 OR +2% Day 2 OR High +2% Day 1 (T+1 tradeable)
"""

import warnings; warnings.filterwarnings("ignore")
import sys, os
import pandas as pd
import numpy as np
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands

conn = psycopg2.connect(DATABASE_URL)
df = pd.read_sql(
    "SELECT symbol, date, open, high, low, close, volume "
    "FROM nasdaq_daily_prices WHERE close > 0 AND volume > 0 "
    "ORDER BY symbol, date", conn)
df["date"] = pd.to_datetime(df["date"])
halal = pd.read_sql("SELECT symbol FROM nasdaq_stocks WHERE halal_status = 'HALAL'", conn)
conn.close()

df = df[df["symbol"].isin(set(halal["symbol"]))]
print(f"Halal: {df.symbol.nunique()} stocks, {len(df)} rows\n")


def t1_win(close, high, price, idx):
    if idx + 2 >= len(close):
        return None
    if (close.iloc[idx + 1] - price) / price * 100 >= 1.5:
        return True
    if (high.iloc[idx + 1] - price) / price * 100 >= 2.0:
        return True
    if (close.iloc[idx + 2] - price) / price * 100 >= 2.0:
        return True
    return False


R = {}
N = {}

def add(k, n, w):
    if k not in R:
        R[k] = []
        N[k] = n
    if w is not None:
        R[k].append(w)


sc = 0
for sym, sdf in df.groupby("symbol"):
    if len(sdf) < 120:
        continue
    sc += 1
    sdf = sdf.sort_values("date").reset_index(drop=True)
    c = sdf["close"]; h = sdf["high"]; l = sdf["low"]; o = sdf["open"]; v = sdf["volume"].astype(float)

    rsi = RSIIndicator(c, window=14).rsi()
    macd_obj = MACD(c); macd_line = macd_obj.macd(); macd_sig = macd_obj.macd_signal(); macd_h = macd_obj.macd_diff()
    ema9 = EMAIndicator(c, window=9).ema_indicator()
    ema21 = EMAIndicator(c, window=21).ema_indicator()
    ema50 = EMAIndicator(c, window=50).ema_indicator()
    sma200 = c.rolling(200).mean()
    bb = BollingerBands(c, window=20, window_dev=2)
    bb_pct = bb.bollinger_pband()
    bb_width = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg() * 100
    adx_obj = ADXIndicator(h, l, c, window=14)
    adx = adx_obj.adx(); pdi = adx_obj.adx_pos(); mdi = adx_obj.adx_neg()
    obv = OnBalanceVolumeIndicator(c, v).on_balance_volume()
    va = v.rolling(20).mean()

    obv_sl = obv.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)
    price_sl = c.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)

    for i in range(60, len(sdf) - 2):
        cv = c.iloc[i]; ov = o.iloc[i]; hv = h.iloc[i]; lv = l.iloc[i]; vv = v.iloc[i]
        cp = c.iloc[i-1]

        rv = rsi.iloc[i] if pd.notna(rsi.iloc[i]) else 50
        mh = macd_h.iloc[i] if pd.notna(macd_h.iloc[i]) else 0
        ml = macd_line.iloc[i] if pd.notna(macd_line.iloc[i]) else 0
        ms = macd_sig.iloc[i] if pd.notna(macd_sig.iloc[i]) else 0
        mh_prev = macd_h.iloc[i-1] if pd.notna(macd_h.iloc[i-1]) else 0
        ml_prev = macd_line.iloc[i-1] if pd.notna(macd_line.iloc[i-1]) else 0
        ms_prev = macd_sig.iloc[i-1] if pd.notna(macd_sig.iloc[i-1]) else 0
        e9 = ema9.iloc[i] if pd.notna(ema9.iloc[i]) else 0
        e21 = ema21.iloc[i] if pd.notna(ema21.iloc[i]) else 0
        e50 = ema50.iloc[i] if pd.notna(ema50.iloc[i]) else 0
        s200 = sma200.iloc[i] if pd.notna(sma200.iloc[i]) else 0
        bpct = bb_pct.iloc[i] if pd.notna(bb_pct.iloc[i]) else 0.5
        bw = bb_width.iloc[i] if pd.notna(bb_width.iloc[i]) else 10
        av = adx.iloc[i] if pd.notna(adx.iloc[i]) else 0
        pd_v = pdi.iloc[i] if pd.notna(pdi.iloc[i]) else 0
        md_v = mdi.iloc[i] if pd.notna(mdi.iloc[i]) else 0
        vav = va.iloc[i] if pd.notna(va.iloc[i]) else vv
        obs = obv_sl.iloc[i] if pd.notna(obv_sl.iloc[i]) else 0
        prs = price_sl.iloc[i] if pd.notna(price_sl.iloc[i]) else 0

        green = cv > ov
        vr = vv / vav if vav > 0 else 1
        ma_al = e9 > e21 > e50 and cv > e9
        above_200 = cv > s200 if s200 > 0 else False
        chg1 = (cv - cp) / cp * 100
        chg5 = (cv - c.iloc[i-5]) / c.iloc[i-5] * 100 if i >= 5 else 0

        # MACD signals
        macd_bull_cross = ml > ms and ml_prev <= ms_prev  # bullish cross
        macd_bear_cross = ml < ms and ml_prev >= ms_prev
        macd_hist_rising = mh > mh_prev and mh_prev < 0  # histogram turning
        macd_hist_positive = mh > 0

        # Fibonacci: compute from recent 60-bar swing
        recent_high = h.iloc[max(0,i-60):i].max()
        recent_low = l.iloc[max(0,i-60):i].min()
        hi_idx = h.iloc[max(0,i-60):i].idxmax()
        lo_idx = l.iloc[max(0,i-60):i].idxmin()
        fib_diff = recent_high - recent_low
        if fib_diff > 0 and lo_idx < hi_idx:  # upswing
            fib_382 = recent_high - fib_diff * 0.382
            fib_500 = recent_high - fib_diff * 0.5
            fib_618 = recent_high - fib_diff * 0.618
            at_fib_382 = abs(cv - fib_382) / fib_382 * 100 < 1.5
            at_fib_500 = abs(cv - fib_500) / fib_500 * 100 < 1.5
            at_fib_618 = abs(cv - fib_618) / fib_618 * 100 < 1.5
            at_any_fib = at_fib_382 or at_fib_500 or at_fib_618
        else:
            at_fib_382 = at_fib_500 = at_fib_618 = at_any_fib = False

        # 20-day breakout
        h20 = h.iloc[max(0,i-20):i].max()
        breakout_20d = cv > h20 and cp <= h20

        # BB squeeze then breakout
        if i >= 5:
            recent_bw = bb_width.iloc[i-20:i].dropna()
            bb_squeeze = bw <= recent_bw.quantile(0.1) if len(recent_bw) > 5 else False
        else:
            bb_squeeze = False

        # Golden cross / Death cross
        golden = e50 > s200 and ema50.iloc[i-1] <= sma200.iloc[i-1] if s200 > 0 and i > 0 and pd.notna(ema50.iloc[i-1]) and pd.notna(sma200.iloc[i-1]) else False
        death = e50 < s200 and ema50.iloc[i-1] >= sma200.iloc[i-1] if s200 > 0 and i > 0 and pd.notna(ema50.iloc[i-1]) and pd.notna(sma200.iloc[i-1]) else False

        # ChoCh + BOS
        swing_highs = [(j, float(h.iloc[j])) for j in range(max(3,i-30), i-3) if h.iloc[j] == max(h.iloc[j-3:j+4])]
        swing_lows = [(j, float(l.iloc[j])) for j in range(max(3,i-30), i-3) if l.iloc[j] == min(l.iloc[j-3:j+4])]
        choch_bos = False
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            if swing_lows[-1][1] < swing_lows[-2][1]:
                if cv > swing_highs[-1][1] and hv > swing_highs[-1][1]:
                    choch_bos = True

        # Liquidity grab
        rl = l.iloc[max(0,i-5):i].min()
        liq = lv < rl * 0.99 and cv > rl

        # Hammer
        body = abs(cv - ov)
        ls = min(cv, ov) - lv
        hammer = ls > body * 2 if body > 0 else False

        # Gap
        gap_down = ov < cp * 0.98
        gap_up = ov > cp * 1.02

        # Consecutive red
        rd = 0
        for j in range(1, min(6, i)):
            if c.iloc[i-j] < c.iloc[i-j-1]: rd += 1
            else: break

        obv_div = prs < 0 and obs > 0

        w = t1_win(c, h, cv, i)

        add("baseline", "Random entry", w)

        # === MACD ===
        if macd_bull_cross: add("macd_bull", "MACD bullish cross", w)
        if macd_bull_cross and rv < 45: add("macd_bull_rsi45", "MACD cross + RSI<45", w)
        if macd_bull_cross and vr > 1.5: add("macd_bull_vol", "MACD cross + Vol>1.5x", w)
        if macd_bull_cross and above_200: add("macd_bull_200", "MACD cross + above SMA200", w)
        if macd_hist_rising and rv < 40: add("macd_rising_rsi", "MACD hist rising + RSI<40", w)
        if macd_hist_rising and green: add("macd_rising_grn", "MACD hist rising + green", w)

        # === FIBONACCI ===
        if at_fib_382 and green: add("fib382_grn", "At Fib 0.382 + green", w)
        if at_fib_500 and green: add("fib500_grn", "At Fib 0.500 + green", w)
        if at_fib_618 and green: add("fib618_grn", "At Fib 0.618 + green", w)
        if at_any_fib and rv < 40: add("fib_rsi40", "At Fib level + RSI<40", w)
        if at_any_fib and green and rv < 45: add("fib_grn_rsi", "Fib + green + RSI<45", w)
        if at_fib_618 and rv < 35: add("fib618_rsi35", "Fib 0.618 + RSI<35 (golden)", w)

        # === BREAKOUT ===
        if breakout_20d: add("break20d", "20-day high breakout", w)
        if breakout_20d and vr > 1.5: add("break20d_vol", "20d breakout + volume", w)
        if breakout_20d and ma_al: add("break20d_ma", "20d breakout + MA aligned", w)
        if breakout_20d and macd_hist_positive: add("break20d_macd", "20d breakout + MACD positive", w)

        # === ADX ===
        if av > 25 and pd_v > md_v: add("adx25_bull", "ADX>25 + bullish DI", w)
        if av > 25 and pd_v > md_v and rv < 50: add("adx_bull_rsi50", "ADX bull + RSI<50", w)
        if av > 30 and pd_v > md_v and ma_al: add("adx30_ma", "ADX>30 + bullDI + MA", w)

        # === BB SQUEEZE ===
        if bb_squeeze and green: add("sq_grn", "BB squeeze + green", w)
        if bb_squeeze and vr > 1.5: add("sq_vol", "BB squeeze + volume", w)
        if bb_squeeze and cv > bb.bollinger_hband().iloc[i] if pd.notna(bb.bollinger_hband().iloc[i]) else False:
            add("sq_break_up", "Squeeze breakout UP", w)

        # === GOLDEN/DEATH CROSS ===
        if golden: add("golden", "Golden cross (SMA50>200)", w)
        if death: add("death", "Death cross (SMA50<200)", w)

        # === ChoCh + BOS ===
        if choch_bos: add("choch_bos", "ChoCh + BOS", w)
        if choch_bos and green: add("choch_grn", "ChoCh+BOS + green", w)
        if choch_bos and vr > 1.5: add("choch_vol", "ChoCh+BOS + vol", w)

        # === EMA BOUNCE ===
        if lv <= e21 * 1.005 and cv > e21 and green and e9 > e21: add("ema21_bounce", "EMA21 bounce (uptrend)", w)
        if lv <= e50 * 1.005 and cv > e50 and green: add("ema50_bounce", "EMA50 bounce", w)
        if s200 > 0 and lv <= s200 * 1.005 and cv > s200 and green: add("sma200_bounce", "SMA200 bounce", w)

        # === COMBOS ===
        if rv < 30 and gap_down and green: add("rsi30_gapdn_grn", "RSI<30+GapDown+Green", w)
        if at_fib_618 and rv < 35 and green: add("fib618_rsi35_grn", "Fib618+RSI<35+Green", w)
        if macd_bull_cross and at_any_fib: add("macd_fib", "MACD cross at Fib level", w)
        if choch_bos and rv < 45 and green: add("choch_rsi_grn", "ChoCh+RSI<45+Green", w)
        if breakout_20d and av > 25 and vr > 1.5: add("break_adx_vol", "Break+ADX>25+Vol", w)
        if macd_hist_rising and at_any_fib and green: add("macd_fib_grn", "MACDrising+Fib+Green", w)
        if hammer and rv < 35 and vr > 1.3: add("ham_rsi_vol", "Hammer+RSI<35+Vol", w)
        if obv_div and rv < 35: add("obv_rsi35", "OBVdiv+RSI<35", w)
        if liq and rv < 30 and green: add("liq_rsi30_grn", "LiqGrab+RSI<30+Green", w)
        if chg1 < -5 and green and vr > 2: add("crash_recover", "Crash-5%+Green+HighVol", w)

    if sc % 50 == 0:
        print(f"  {sc} stocks done...")

print(f"\n{sc} stocks processed\n")

# Results
print("=" * 70)
print("NASDAQ DEEP BACKTEST: MACD, Fibonacci, Breakouts, ICT, ADX, BB")
print("WIN = +1.5% Day1 close OR +2% Day1 high OR +2% Day2 close")
print("=" * 70)

rows = []
for k, ws in R.items():
    if len(ws) < 30:
        rows.append({"name": N[k], "n": len(ws), "wr": 0, "note": f"few({len(ws)})"})
        continue
    rows.append({"name": N[k], "n": len(ws), "wr": sum(ws)/len(ws)*100})

rows.sort(key=lambda x: -x.get("wr", 0))

print(f"\n{'Rk':>3} {'Strategy':<42s} {'Events':>8s} {'Win%':>7s}")
print("-" * 65)
for i, r in enumerate(rows, 1):
    if "note" in r:
        print(f"{i:3d} {r['name']:<42s} {r['n']:8d}    {r['note']}")
    else:
        m = " ***" if r["wr"] >= 50 else " **" if r["wr"] >= 45 else " *" if r["wr"] >= 40 else ""
        print(f"{i:3d} {r['name']:<42s} {r['n']:8d} {r['wr']:6.1f}%{m}")

print(f"\nBaseline: {sum(R['baseline'])/len(R['baseline'])*100:.1f}%")
