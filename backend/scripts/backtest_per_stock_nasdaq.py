#!/usr/bin/env python3
"""Per-stock NASDAQ strategy profiling. Find what works for EACH stock."""

import warnings; warnings.filterwarnings("ignore")
import sys, os
import pandas as pd
import numpy as np
import psycopg2, psycopg2.extras, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

from ta.momentum import RSIIndicator
from ta.volume import OnBalanceVolumeIndicator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands

conn = psycopg2.connect(DATABASE_URL)
df = pd.read_sql(
    "SELECT symbol, date, open, high, low, close, volume "
    "FROM nasdaq_daily_prices WHERE close > 0 AND volume > 0 "
    "ORDER BY symbol, date", conn)
df["date"] = pd.to_datetime(df["date"])
halal = pd.read_sql("SELECT symbol, halal_status, name, sector, industry FROM nasdaq_stocks WHERE halal_status = 'HALAL'", conn)
halal_info = dict(zip(halal["symbol"], halal[["name", "sector", "industry"]].to_dict("records")))
conn.close()

df = df[df["symbol"].isin(set(halal["symbol"]))]
print(f"Stocks: {df.symbol.nunique()}, Rows: {len(df)}\n")

STRATS = [
    "RSI<30", "RSI<35", "RSI<40",
    "RSI30+GapDn+Grn", "RSI30+LiqGrab+Grn",
    "Crash5%+Grn+Vol", "Hammer+RSI35+Vol",
    "3Red", "5dDrop5%", "5dDrop10%",
    "MACDcross", "MACDcross+Vol", "MACDcross+RSI45",
    "MACDrising+RSI40",
    "Break20d", "Break20d+Vol", "Break20d+MACD",
    "ADX25+BullDI", "ADX25+BullDI+RSI50",
    "ChoCh+BOS", "ChoCh+BOS+Grn",
    "EMA21bounce", "EMA50bounce", "SMA200bounce",
    "BBsqueeze+Grn", "BBsqueeze+Vol",
    "VolSpike+Grn", "OBVdiv+RSI35",
    "GapDn+Grn", "GapDn+Vol+Grn",
    "Fib618+Grn", "Fib500+Grn",
    "LiqGrab+Grn",
]


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


all_profiles = []
sc = 0

for sym, sdf in df.groupby("symbol"):
    if len(sdf) < 100:
        continue
    sc += 1
    sdf = sdf.sort_values("date").reset_index(drop=True)
    c = sdf["close"]; h = sdf["high"]; l = sdf["low"]; o = sdf["open"]; v = sdf["volume"].astype(float)

    rsi = RSIIndicator(c, window=14).rsi()
    macd_obj = MACD(c); ml = macd_obj.macd(); ms = macd_obj.macd_signal(); mh = macd_obj.macd_diff()
    e9 = EMAIndicator(c, window=9).ema_indicator()
    e21 = EMAIndicator(c, window=21).ema_indicator()
    e50 = EMAIndicator(c, window=50).ema_indicator()
    s200 = c.rolling(200).mean()
    bb = BollingerBands(c, window=20, window_dev=2)
    bb_pct = bb.bollinger_pband()
    bb_w = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg() * 100
    adx_o = ADXIndicator(h, l, c, window=14)
    adx = adx_o.adx(); pdi = adx_o.adx_pos(); mdi = adx_o.adx_neg()
    obv = OnBalanceVolumeIndicator(c, v).on_balance_volume()
    va = v.rolling(20).mean()
    obv_sl = obv.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)
    price_sl = c.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True)

    strat_wins = {s: [] for s in STRATS}

    for i in range(60, len(sdf) - 2):
        cv, ov, hv, lv, vv = c.iloc[i], o.iloc[i], h.iloc[i], l.iloc[i], v.iloc[i]
        cp = c.iloc[i-1]
        rv = rsi.iloc[i] if pd.notna(rsi.iloc[i]) else 50
        mhv = mh.iloc[i] if pd.notna(mh.iloc[i]) else 0
        mlv = ml.iloc[i] if pd.notna(ml.iloc[i]) else 0
        msv = ms.iloc[i] if pd.notna(ms.iloc[i]) else 0
        mh_p = mh.iloc[i-1] if pd.notna(mh.iloc[i-1]) else 0
        ml_p = ml.iloc[i-1] if pd.notna(ml.iloc[i-1]) else 0
        ms_p = ms.iloc[i-1] if pd.notna(ms.iloc[i-1]) else 0
        e9v = e9.iloc[i] if pd.notna(e9.iloc[i]) else 0
        e21v = e21.iloc[i] if pd.notna(e21.iloc[i]) else 0
        e50v = e50.iloc[i] if pd.notna(e50.iloc[i]) else 0
        s200v = s200.iloc[i] if pd.notna(s200.iloc[i]) else 0
        bpv = bb_pct.iloc[i] if pd.notna(bb_pct.iloc[i]) else 0.5
        avv = adx.iloc[i] if pd.notna(adx.iloc[i]) else 0
        pdv = pdi.iloc[i] if pd.notna(pdi.iloc[i]) else 0
        mdv = mdi.iloc[i] if pd.notna(mdi.iloc[i]) else 0
        vav = va.iloc[i] if pd.notna(va.iloc[i]) else vv
        obs = obv_sl.iloc[i] if pd.notna(obv_sl.iloc[i]) else 0
        prs = price_sl.iloc[i] if pd.notna(price_sl.iloc[i]) else 0

        grn = cv > ov
        vr = vv / vav if vav > 0 else 1
        chg1 = (cv - cp) / cp * 100
        chg5 = (cv - c.iloc[i-5]) / c.iloc[i-5] * 100 if i >= 5 else 0
        body = abs(cv - ov)
        ls = min(cv, ov) - lv
        ham = ls > body * 2 if body > 0 else False
        gap_dn = ov < cp * 0.98
        rl = l.iloc[max(0,i-5):i].min()
        liq = lv < rl * 0.99 and cv > rl
        macd_cross = mlv > msv and ml_p <= ms_p
        macd_rising = mhv > mh_p and mh_p < 0
        h20 = h.iloc[max(0,i-20):i].max()
        break20 = cv > h20 and cp <= h20
        rd = 0
        for j in range(1, min(6, i)):
            if c.iloc[i-j] < c.iloc[i-j-1]: rd += 1
            else: break

        # Fib
        rh = h.iloc[max(0,i-60):i].max(); rlo = l.iloc[max(0,i-60):i].min()
        hi_idx = h.iloc[max(0,i-60):i].idxmax(); lo_idx = l.iloc[max(0,i-60):i].idxmin()
        fd = rh - rlo
        f618 = rh - fd * 0.618 if fd > 0 and lo_idx < hi_idx else 0
        f500 = rh - fd * 0.5 if fd > 0 and lo_idx < hi_idx else 0
        at618 = abs(cv - f618) / f618 * 100 < 1.5 if f618 > 0 else False
        at500 = abs(cv - f500) / f500 * 100 < 1.5 if f500 > 0 else False

        # ChoCh+BOS
        shs = [(j, float(h.iloc[j])) for j in range(max(3,i-30), i-3) if h.iloc[j] == max(h.iloc[j-3:j+4])]
        sls = [(j, float(l.iloc[j])) for j in range(max(3,i-30), i-3) if l.iloc[j] == min(l.iloc[j-3:j+4])]
        choch = False
        if len(shs) >= 2 and len(sls) >= 2:
            if sls[-1][1] < sls[-2][1] and cv > shs[-1][1] and hv > shs[-1][1]:
                choch = True

        # BB squeeze
        bwv = bb_w.iloc[i] if pd.notna(bb_w.iloc[i]) else 10
        rec_bw = bb_w.iloc[max(0,i-20):i].dropna()
        sq = bwv <= rec_bw.quantile(0.1) if len(rec_bw) > 5 else False

        obv_div = prs < 0 and obs > 0

        w = t1_win(c, h, cv, i)
        if w is None:
            continue

        if rv < 30: strat_wins["RSI<30"].append(w)
        if rv < 35: strat_wins["RSI<35"].append(w)
        if rv < 40: strat_wins["RSI<40"].append(w)
        if rv < 30 and gap_dn and grn: strat_wins["RSI30+GapDn+Grn"].append(w)
        if liq and rv < 30 and grn: strat_wins["RSI30+LiqGrab+Grn"].append(w)
        if chg1 < -5 and grn and vr > 2: strat_wins["Crash5%+Grn+Vol"].append(w)
        if ham and rv < 35 and vr > 1.3: strat_wins["Hammer+RSI35+Vol"].append(w)
        if rd >= 3: strat_wins["3Red"].append(w)
        if chg5 < -5: strat_wins["5dDrop5%"].append(w)
        if chg5 < -10: strat_wins["5dDrop10%"].append(w)
        if macd_cross: strat_wins["MACDcross"].append(w)
        if macd_cross and vr > 1.5: strat_wins["MACDcross+Vol"].append(w)
        if macd_cross and rv < 45: strat_wins["MACDcross+RSI45"].append(w)
        if macd_rising and rv < 40: strat_wins["MACDrising+RSI40"].append(w)
        if break20: strat_wins["Break20d"].append(w)
        if break20 and vr > 1.5: strat_wins["Break20d+Vol"].append(w)
        if break20 and mhv > 0: strat_wins["Break20d+MACD"].append(w)
        if avv > 25 and pdv > mdv: strat_wins["ADX25+BullDI"].append(w)
        if avv > 25 and pdv > mdv and rv < 50: strat_wins["ADX25+BullDI+RSI50"].append(w)
        if choch: strat_wins["ChoCh+BOS"].append(w)
        if choch and grn: strat_wins["ChoCh+BOS+Grn"].append(w)
        if lv <= e21v * 1.005 and cv > e21v and grn and e9v > e21v: strat_wins["EMA21bounce"].append(w)
        if lv <= e50v * 1.005 and cv > e50v and grn: strat_wins["EMA50bounce"].append(w)
        if s200v > 0 and lv <= s200v * 1.005 and cv > s200v and grn: strat_wins["SMA200bounce"].append(w)
        if sq and grn: strat_wins["BBsqueeze+Grn"].append(w)
        if sq and vr > 1.5: strat_wins["BBsqueeze+Vol"].append(w)
        if vr > 2 and grn: strat_wins["VolSpike+Grn"].append(w)
        if obv_div and rv < 35: strat_wins["OBVdiv+RSI35"].append(w)
        if gap_dn and grn: strat_wins["GapDn+Grn"].append(w)
        if gap_dn and grn and vr > 1.5: strat_wins["GapDn+Vol+Grn"].append(w)
        if at618 and grn: strat_wins["Fib618+Grn"].append(w)
        if at500 and grn: strat_wins["Fib500+Grn"].append(w)
        if liq and grn: strat_wins["LiqGrab+Grn"].append(w)

    # Build profile
    info = halal_info.get(sym, {})
    profile = {"symbol": sym, "name": info.get("name", ""), "sector": info.get("sector", "")}
    best_s = None
    best_wr = 0

    for s in STRATS:
        ws = strat_wins[s]
        if len(ws) >= 3:
            wr = sum(ws) / len(ws) * 100
            profile[f"{s}_n"] = len(ws)
            profile[f"{s}_wr"] = round(wr, 0)
            if wr > best_wr and len(ws) >= 5:
                best_wr = wr
                best_s = s

    profile["best_strategy"] = best_s
    profile["best_wr"] = round(best_wr, 0)
    all_profiles.append(profile)

    if sc % 50 == 0:
        print(f"  {sc} stocks...")

print(f"\n{sc} stocks processed\n")

pdf = pd.DataFrame(all_profiles)

# Save to DB for the signal system
conn2 = psycopg2.connect(DATABASE_URL)
conn2.autocommit = True
cur = conn2.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS nasdaq_stock_profiles (symbol TEXT PRIMARY KEY, profile JSONB, best_strategy TEXT, best_wr DOUBLE PRECISION)")
for _, r in pdf.iterrows():
    cur.execute(
        "INSERT INTO nasdaq_stock_profiles (symbol, profile, best_strategy, best_wr) VALUES (%s, %s, %s, %s) ON CONFLICT (symbol) DO UPDATE SET profile=EXCLUDED.profile, best_strategy=EXCLUDED.best_strategy, best_wr=EXCLUDED.best_wr",
        (r["symbol"], json.dumps(r.to_dict()), r["best_strategy"], r["best_wr"])
    )
conn2.close()
print("Saved profiles to DB\n")

# Output
print("=" * 80)
print("NASDAQ PER-STOCK PROFILES — Best strategy for each halal stock")
print("WIN = +1.5% Day1 OR +2% Day2 (T+1 metric)")
print("=" * 80)

# 70%+ win rate
top = pdf[pdf["best_wr"] >= 70].sort_values("best_wr", ascending=False)
print(f"\n70%+ WIN RATE ({len(top)} stocks):")
print(f"{'Stock':<8s} {'Name':<30s} {'Sector':<20s} {'Best Strategy':<25s} {'WR':>5s} {'N':>4s}")
print("-" * 95)
for _, r in top.head(40).iterrows():
    s = r["best_strategy"] or ""
    n = r.get(f"{s}_n", 0) if s else 0
    print(f"{r['symbol']:<8s} {str(r['name'])[:29]:<30s} {str(r['sector'])[:19]:<20s} {s:<25s} {r['best_wr']:4.0f}% {n:4.0f}")

# 60%+
mid = pdf[(pdf["best_wr"] >= 60) & (pdf["best_wr"] < 70)].sort_values("best_wr", ascending=False)
print(f"\n60-70% WIN RATE ({len(mid)} stocks):")
for _, r in mid.head(30).iterrows():
    s = r["best_strategy"] or ""
    n = r.get(f"{s}_n", 0) if s else 0
    print(f"  {r['symbol']:<8s} {s:<25s} {r['best_wr']:4.0f}% ({n:.0f} events) {str(r['sector'])[:20]}")

# Per strategy: top stocks
print(f"\n{'=' * 80}")
print("TOP 3 STOCKS PER STRATEGY")
print("=" * 80)
for strat in STRATS:
    wr_col = f"{strat}_wr"
    n_col = f"{strat}_n"
    if wr_col not in pdf.columns:
        continue
    valid = pdf[(pdf[wr_col].notna()) & (pdf.get(n_col, 0) >= 5)].sort_values(wr_col, ascending=False)
    if len(valid) == 0:
        continue
    t3 = valid.head(3)
    avg = valid[wr_col].mean()
    print(f"\n{strat} (avg: {avg:.0f}%, {len(valid)} stocks):")
    for _, r in t3.iterrows():
        print(f"  {r['symbol']:<8s} {r[wr_col]:.0f}% ({r[n_col]:.0f} events)")

# Summary
print(f"\n{'=' * 80}")
print("SUMMARY")
print(f"Total halal stocks profiled: {len(pdf)}")
print(f"Stocks with 70%+ best strategy: {len(top)}")
print(f"Stocks with 60%+ best strategy: {len(top) + len(mid)}")
print(f"Stocks with 50%+ best strategy: {len(pdf[pdf['best_wr'] >= 50])}")
