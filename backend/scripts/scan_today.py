#!/usr/bin/env python3
"""Scan for NASDAQ halal buy signals RIGHT NOW with entry/target/SL prices."""

import warnings; warnings.filterwarnings("ignore")
import sys, os
import pandas as pd, numpy as np, psycopg2, psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL
from ta.momentum import RSIIndicator

dict_conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = dict_conn.cursor()
cur.execute("SELECT symbol, name, sector FROM nasdaq_stocks WHERE halal_status = 'HALAL'")
halal = {r["symbol"]: r for r in cur.fetchall()}
cur.close()
dict_conn.close()

# Use plain connection for pd.read_sql (RealDictCursor causes date parsing issues)
plain_conn = psycopg2.connect(DATABASE_URL)
df = pd.read_sql(
    "SELECT symbol, date, open, high, low, close, volume "
    "FROM nasdaq_daily_prices WHERE close > 0 AND volume > 0 "
    "ORDER BY symbol, date", plain_conn)
plain_conn.close()
df["date"] = pd.to_datetime(df["date"])
df = df[df["symbol"].isin(halal)]

print(f"Scanning {df.symbol.nunique()} halal stocks...\n")

signals = []

for sym, sdf in df.groupby("symbol"):
    if len(sdf) < 30:
        continue
    sdf = sdf.sort_values("date").reset_index(drop=True)
    c = sdf["close"]; h = sdf["high"]; l = sdf["low"]; o = sdf["open"]; v = sdf["volume"].astype(float)
    rsi = RSIIndicator(c, window=14).rsi()
    va = v.rolling(20).mean()

    i = len(sdf) - 1
    cv = float(c.iloc[i])
    ov = float(o.iloc[i])
    hv = float(h.iloc[i])
    lv = float(l.iloc[i])
    vv = float(v.iloc[i])
    cp = float(c.iloc[i-1])
    rv = float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else 50
    vav = float(va.iloc[i]) if pd.notna(va.iloc[i]) else vv
    vr = vv / vav if vav > 0 else 1
    grn = cv > ov
    chg1 = (cv - cp) / cp * 100
    chg5 = (cv - float(c.iloc[i-5])) / float(c.iloc[i-5]) * 100 if i >= 5 else 0
    gap_dn = ov < cp * 0.98
    rl = float(l.iloc[max(0,i-5):i].min())
    liq = lv < rl * 0.99 and cv > rl
    dt = str(sdf["date"].iloc[i].date())
    info = halal.get(sym, {})

    # ATR for SL calculation
    recent_close = c.iloc[-6:].values
    atr5 = float(np.mean(np.abs(np.diff(recent_close)))) if len(recent_close) > 1 else cv * 0.02

    matched = []
    tier = 3

    # TIER 1: 70%+ win
    if rv < 30 and gap_dn and grn:
        matched.append("RSI<30+GapDown+Green [72%]")
        tier = 1
    if liq and rv < 30 and grn:
        matched.append("LiqGrab+RSI<30+Green [62%]")
        tier = min(tier, 1)

    # TIER 2: 50-60%
    if chg1 < -5 and grn and vr > 2:
        matched.append("Crash-5%+Green+HighVol [58%]")
        tier = min(tier, 2)
    if chg5 < -10:
        matched.append("5dDrop>10% [64%]")
        tier = min(tier, 2)
    if chg1 < -5:
        matched.append("Today-5% [61%]")
        tier = min(tier, 2)
    if gap_dn and grn and vr > 1.5:
        matched.append("GapDown+Vol+Green [59%]")
        tier = min(tier, 2)

    # TIER 3: 44-50%
    if rv < 30 and vr > 1.5 and grn:
        matched.append("RSI<30+Vol+Green [57%]")
        tier = min(tier, 2)

    body = abs(cv - ov)
    ls = min(cv, ov) - lv
    ham = ls > body * 2 if body > 0 else False
    if ham and rv < 35 and vr > 1.3:
        matched.append("Hammer+RSI<35+Vol [50%]")
        tier = min(tier, 2)

    if not matched:
        continue

    target = round(cv * 1.02, 2)
    sl = round(cv - atr5 * 1.5, 2)
    risk_pct = round((cv - sl) / cv * 100, 1)

    signals.append({
        "sym": sym,
        "name": info.get("name", ""),
        "sector": info.get("sector", ""),
        "price": cv,
        "date": dt,
        "rsi": round(rv, 1),
        "chg1": round(chg1, 1),
        "chg5": round(chg5, 1),
        "vol": round(vr, 1),
        "tier": tier,
        "target": target,
        "sl": sl,
        "risk": risk_pct,
        "signals": matched,
    })

signals.sort(key=lambda x: (x["tier"], -len(x["signals"])))

print("=" * 90)
print("NASDAQ HALAL BUY SIGNALS — LATEST DATA")
print("=" * 90)

if not signals:
    print("\nNo signals today. The proven setups only fire on crash/dip days.")
    print("This is GOOD — it means we're patient and only trade high-probability setups.")
else:
    for s in signals:
        sigs = " | ".join(s["signals"])
        print(f"\nTIER {s['tier']}: {s['sym']} ({s['name'][:30]})")
        print(f"  Sector: {s['sector']}")
        print(f"  Price: ${s['price']:.2f} | RSI: {s['rsi']:.0f} | Today: {s['chg1']:+.1f}% | 5D: {s['chg5']:+.1f}% | Vol: {s['vol']}x")
        print(f"  BUY:    ${s['price']:.2f}")
        print(f"  TARGET: ${s['target']:.2f} (+2.0%)")
        print(f"  SL:     ${s['sl']:.2f} (-{s['risk']}%)")
        print(f"  Signals: {sigs}")

print(f"\nTotal: {len(signals)} signals | Tier 1: {sum(1 for s in signals if s['tier']==1)} | Tier 2: {sum(1 for s in signals if s['tier']==2)}")
