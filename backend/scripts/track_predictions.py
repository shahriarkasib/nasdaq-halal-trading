#!/usr/bin/env python3
"""
Track predictions — updates current prices and calculates outcomes.
Run daily to see how our predictions are performing.
"""

import warnings; warnings.filterwarnings("ignore")
import sys, os
import psycopg2, psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

try:
    import yfinance as yf
except ImportError:
    print("Install yfinance: pip install yfinance")
    sys.exit(1)

conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
cur = conn.cursor()

# Get all active predictions (last 10 days)
cur.execute("""
    SELECT id, symbol, signal_date, entry_price, target_price, stop_loss,
           days_tracked, max_price, min_price
    FROM nasdaq_predictions
    WHERE signal_date >= CURRENT_DATE - INTERVAL '10 days'
    ORDER BY signal_date DESC, symbol
""")
preds = cur.fetchall()

if not preds:
    print("No active predictions to track.")
    conn.close()
    sys.exit(0)

print(f"Tracking {len(preds)} predictions...\n")

# Get current prices via yfinance
symbols = list(set(p["symbol"] for p in preds))
print(f"Fetching live prices for {len(symbols)} stocks...")

prices = {}
for sym in symbols:
    try:
        t = yf.Ticker(sym)
        hist = t.history(period="5d")
        if not hist.empty:
            prices[sym] = {
                "current": float(hist["Close"].iloc[-1]),
                "high_5d": float(hist["High"].max()),
                "low_5d": float(hist["Low"].min()),
                "closes": [float(hist["Close"].iloc[i]) for i in range(len(hist))],
            }
    except Exception as e:
        print(f"  {sym}: fetch failed ({e})")

print(f"Got prices for {len(prices)} stocks\n")

# Update each prediction
print("=" * 95)
print("PREDICTION TRACKER")
print("=" * 95)
print(f"\n{'Symbol':<8s} {'Signal':<12s} {'Entry':>8s} {'Current':>8s} {'Chg%':>7s} {'Max%':>6s} {'Min%':>7s} {'Days':>5s} {'Target':>8s} {'SL':>8s} {'Status':<12s}")
print("-" * 95)

wins = 0
losses = 0
pending = 0

for p in preds:
    sym = p["symbol"]
    entry = p["entry_price"]
    target = p["target_price"]
    sl = p["stop_loss"]

    if sym not in prices:
        continue

    pr = prices[sym]
    current = pr["current"]
    high = pr["high_5d"]
    low = pr["low_5d"]

    # Update max/min tracking
    old_max = p["max_price"] or 0
    old_min = p["min_price"] or 999999
    new_max = max(old_max, high)
    new_min = min(old_min, low)

    chg_pct = (current - entry) / entry * 100
    max_gain = (new_max - entry) / entry * 100
    max_loss = (new_min - entry) / entry * 100

    # Determine outcome
    hit_target = new_max >= target
    hit_sl = new_min <= sl

    from datetime import date
    days = (date.today() - p["signal_date"]).days

    if hit_target and not hit_sl:
        outcome = "WIN"
        wins += 1
    elif hit_sl and not hit_target:
        outcome = "LOSS"
        losses += 1
    elif hit_target and hit_sl:
        outcome = "MIXED"
        pending += 1
    else:
        outcome = "PENDING"
        pending += 1

    # Assign day closes
    closes = pr["closes"]
    d1 = closes[0] if len(closes) > 0 else None
    d2 = closes[1] if len(closes) > 1 else None
    d3 = closes[2] if len(closes) > 2 else None
    d5 = closes[4] if len(closes) > 4 else None

    # Update DB
    cur.execute("""
        UPDATE nasdaq_predictions SET
            current_price = %s,
            day1_close = COALESCE(day1_close, %s),
            day2_close = COALESCE(day2_close, %s),
            day3_close = COALESCE(day3_close, %s),
            day5_close = COALESCE(day5_close, %s),
            max_price = %s, min_price = %s,
            max_gain_pct = %s, max_loss_pct = %s,
            hit_target = %s, hit_stoploss = %s,
            days_tracked = %s, outcome = %s,
            last_tracked = CURRENT_DATE
        WHERE id = %s
    """, (current, d1, d2, d3, d5, new_max, new_min,
          round(max_gain, 2), round(max_loss, 2),
          hit_target, hit_sl, days, outcome, p["id"]))

    status_color = "WIN ✓" if outcome == "WIN" else "LOSS ✗" if outcome == "LOSS" else "PENDING..."
    print(f"{sym:<8s} {str(p['signal_date']):<12s} ${entry:>7.2f} ${current:>7.2f} {chg_pct:+6.1f}% {max_gain:+5.1f}% {max_loss:+6.1f}% {days:5d} ${target:>7.2f} ${sl:>7.2f} {status_color}")

conn.commit()
cur.close()
conn.close()

total = wins + losses + pending
print(f"\n{'=' * 95}")
print(f"SUMMARY: {wins} WINS | {losses} LOSSES | {pending} PENDING | Total: {total}")
if wins + losses > 0:
    print(f"Win Rate So Far: {wins/(wins+losses)*100:.0f}%")
print(f"Expected Win Rate: 64% (from backtest)")
