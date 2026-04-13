#!/usr/bin/env python3
"""Set up NASDAQ database tables."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from config import DATABASE_URL

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

tables = [
    """CREATE TABLE IF NOT EXISTS nasdaq_stocks (
        symbol TEXT PRIMARY KEY,
        name TEXT,
        sector TEXT,
        industry TEXT,
        market_cap BIGINT,
        pe_ratio DOUBLE PRECISION,
        eps DOUBLE PRECISION,
        dividend_yield DOUBLE PRECISION,
        debt_to_equity DOUBLE PRECISION,
        debt_to_market_cap DOUBLE PRECISION,
        revenue BIGINT,
        net_income BIGINT,
        free_cash_flow BIGINT,
        beta DOUBLE PRECISION,
        avg_volume BIGINT,
        high_52w DOUBLE PRECISION,
        low_52w DOUBLE PRECISION,
        halal_status TEXT DEFAULT 'UNKNOWN',
        halal_reason TEXT,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    )""",

    """CREATE TABLE IF NOT EXISTS nasdaq_daily_prices (
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        open DOUBLE PRECISION,
        high DOUBLE PRECISION,
        low DOUBLE PRECISION,
        close DOUBLE PRECISION,
        volume BIGINT,
        adj_close DOUBLE PRECISION,
        PRIMARY KEY (symbol, date)
    )""",

    """CREATE TABLE IF NOT EXISTS nasdaq_indicators (
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        timeframe TEXT NOT NULL DEFAULT 'daily',
        rsi_14 DOUBLE PRECISION,
        macd_line DOUBLE PRECISION,
        macd_signal DOUBLE PRECISION,
        macd_hist DOUBLE PRECISION,
        ema_9 DOUBLE PRECISION,
        ema_21 DOUBLE PRECISION,
        ema_50 DOUBLE PRECISION,
        sma_200 DOUBLE PRECISION,
        bb_upper DOUBLE PRECISION,
        bb_lower DOUBLE PRECISION,
        bb_pct DOUBLE PRECISION,
        atr_14 DOUBLE PRECISION,
        atr_pct DOUBLE PRECISION,
        obv DOUBLE PRECISION,
        cmf_20 DOUBLE PRECISION,
        adx_14 DOUBLE PRECISION,
        vol_ratio DOUBLE PRECISION,
        chg_1d DOUBLE PRECISION,
        chg_5d DOUBLE PRECISION,
        chg_20d DOUBLE PRECISION,
        PRIMARY KEY (symbol, date, timeframe)
    )""",

    """CREATE TABLE IF NOT EXISTS nasdaq_earnings (
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        eps_estimate DOUBLE PRECISION,
        eps_actual DOUBLE PRECISION,
        surprise_pct DOUBLE PRECISION,
        revenue_estimate BIGINT,
        revenue_actual BIGINT,
        price_before DOUBLE PRECISION,
        price_after DOUBLE PRECISION,
        price_change_pct DOUBLE PRECISION,
        PRIMARY KEY (symbol, date)
    )""",

    """CREATE TABLE IF NOT EXISTS nasdaq_signals (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        date DATE NOT NULL DEFAULT CURRENT_DATE,
        signal_type TEXT NOT NULL,
        confidence DOUBLE PRECISION,
        entry_price DOUBLE PRECISION,
        stop_loss DOUBLE PRECISION,
        target DOUBLE PRECISION,
        reasoning TEXT,
        halal_ok BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )""",

    "CREATE INDEX IF NOT EXISTS idx_nasdaq_dp_date ON nasdaq_daily_prices(date)",
    "CREATE INDEX IF NOT EXISTS idx_nasdaq_dp_sym ON nasdaq_daily_prices(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_nasdaq_ind_date ON nasdaq_indicators(date, timeframe)",
    "CREATE INDEX IF NOT EXISTS idx_nasdaq_sig_date ON nasdaq_signals(date)",
    "CREATE INDEX IF NOT EXISTS idx_nasdaq_stocks_halal ON nasdaq_stocks(halal_status)",
]

for sql in tables:
    try:
        cur.execute(sql)
        print(f"OK: {sql[:60]}...")
    except Exception as e:
        print(f"ERR: {e}")

cur.close()
conn.close()
print("\nDatabase setup complete.")
