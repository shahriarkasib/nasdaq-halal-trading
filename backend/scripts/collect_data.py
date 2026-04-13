#!/usr/bin/env python3
"""
Collect NASDAQ/NYSE stock data from Yahoo Finance.
Downloads price history + fundamentals + halal screening.

Usage:
    python3 scripts/collect_data.py --universe sp500
    python3 scripts/collect_data.py --symbols NVDA,GOOGL,AMZN
    python3 scripts/collect_data.py --universe nasdaq100
"""

import sys, os, time, argparse, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

from config import (DATABASE_URL, HARAM_INDUSTRIES, HARAM_TICKERS,
                    HALAL_MAX_DEBT_RATIO, YF_DELAY)

try:
    import yfinance as yf
except ImportError:
    log.error("yfinance not installed. Run: pip install yfinance")
    sys.exit(1)


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_universe(name: str) -> list[str]:
    """Get list of stock symbols for a universe."""
    if name == "sp500":
        import pandas as pd
        try:
            table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
            return sorted(table[0]["Symbol"].str.replace(".", "-").tolist())
        except Exception:
            log.warning("Could not fetch S&P 500 list, using cached top 100")
            return _TOP_100

    elif name == "nasdaq100":
        import pandas as pd
        try:
            table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
            return sorted(table[4]["Ticker"].tolist())
        except Exception:
            return _TOP_100

    elif name == "top50":
        return _TOP_50

    return _TOP_50


_TOP_50 = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "LLY",
    "JPM", "V", "UNH", "MA", "HD", "PG", "COST", "ABBV", "NFLX", "CRM",
    "AMD", "PLTR", "SOFI", "IONQ", "LITE", "COHR", "IPGP", "CMC",
    "MU", "QCOM", "INTC", "AMAT", "LRCX", "KLAC", "MRVL", "SNPS",
    "PANW", "CRWD", "ZS", "FTNT", "NET", "DDOG", "SNOW", "MDB",
    "ABNB", "UBER", "DASH", "RBLX", "SQ", "COIN", "SHOP",
]

_TOP_100 = _TOP_50 + [
    "WMT", "JNJ", "XOM", "PEP", "KO", "MCD", "DIS", "ADBE", "PYPL",
    "T", "VZ", "CMCSA", "ORCL", "IBM", "TXN", "NOW", "INTU", "ISRG",
    "REGN", "VRTX", "MRNA", "GILD", "BIIB", "BMY", "PFE", "TMO",
    "DHR", "ABT", "SYK", "MDT", "ZTS", "CI", "ELV", "HCA",
    "CAT", "DE", "GE", "HON", "MMM", "UPS", "FDX", "RTX",
    "BA", "LMT", "NOC", "GD", "TDG", "SPG", "AMT", "CCI",
]


def screen_halal(info: dict, symbol: str) -> tuple[str, str]:
    """Screen a stock for halal compliance."""
    # Explicit haram list
    if symbol in HARAM_TICKERS:
        return "HARAM", f"Explicitly excluded: {symbol}"

    industry = info.get("industry", "") or ""
    sector = info.get("sector", "") or ""

    # Industry check
    if industry in HARAM_INDUSTRIES:
        return "HARAM", f"Haram industry: {industry}"

    # Sector-level check
    if sector in ("Financial Services",):
        if "bank" in industry.lower() or "insurance" in industry.lower() or "credit" in industry.lower():
            return "HARAM", f"Financial sector: {industry}"

    # Debt ratio check
    market_cap = info.get("marketCap", 0) or 0
    total_debt = info.get("totalDebt", 0) or 0
    if market_cap > 0 and total_debt > 0:
        debt_ratio = total_debt / market_cap
        if debt_ratio > HALAL_MAX_DEBT_RATIO:
            return "DOUBTFUL", f"Debt/MarketCap = {debt_ratio:.1%} > 33%"

    return "HALAL", "Passes all screens"


def collect_stock(conn, symbol: str):
    """Collect data for one stock."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            log.warning(f"  {symbol}: No data from Yahoo Finance")
            return False

        # Halal screening
        halal_status, halal_reason = screen_halal(info, symbol)

        # Store fundamentals
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO nasdaq_stocks (
                symbol, name, sector, industry, market_cap,
                pe_ratio, eps, dividend_yield, debt_to_equity,
                debt_to_market_cap, revenue, net_income, free_cash_flow,
                beta, avg_volume, high_52w, low_52w,
                halal_status, halal_reason
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (symbol) DO UPDATE SET
                name=EXCLUDED.name, sector=EXCLUDED.sector, industry=EXCLUDED.industry,
                market_cap=EXCLUDED.market_cap, pe_ratio=EXCLUDED.pe_ratio, eps=EXCLUDED.eps,
                dividend_yield=EXCLUDED.dividend_yield, debt_to_equity=EXCLUDED.debt_to_equity,
                debt_to_market_cap=EXCLUDED.debt_to_market_cap,
                revenue=EXCLUDED.revenue, net_income=EXCLUDED.net_income,
                free_cash_flow=EXCLUDED.free_cash_flow, beta=EXCLUDED.beta,
                avg_volume=EXCLUDED.avg_volume, high_52w=EXCLUDED.high_52w, low_52w=EXCLUDED.low_52w,
                halal_status=EXCLUDED.halal_status, halal_reason=EXCLUDED.halal_reason,
                updated_at=NOW()
        """, (
            symbol,
            info.get("longName") or info.get("shortName"),
            info.get("sector"),
            info.get("industry"),
            info.get("marketCap"),
            info.get("trailingPE"),
            info.get("trailingEps"),
            info.get("dividendYield"),
            info.get("debtToEquity"),
            (info.get("totalDebt", 0) or 0) / max(info.get("marketCap", 1), 1),
            info.get("totalRevenue"),
            info.get("netIncomeToCommon"),
            info.get("freeCashflow"),
            info.get("beta"),
            info.get("averageVolume"),
            info.get("fiftyTwoWeekHigh"),
            info.get("fiftyTwoWeekLow"),
            halal_status,
            halal_reason,
        ))
        conn.commit()

        # Download price history (2 years)
        hist = ticker.history(period="2y", interval="1d")
        if hist.empty:
            log.warning(f"  {symbol}: No price history")
            return True

        rows = []
        for dt, row in hist.iterrows():
            rows.append((
                symbol, dt.date(),
                round(float(row["Open"]), 4), round(float(row["High"]), 4),
                round(float(row["Low"]), 4), round(float(row["Close"]), 4),
                int(row["Volume"]),
                round(float(row.get("Close", row["Close"])), 4),
            ))

        psycopg2.extras.execute_batch(cur, """
            INSERT INTO nasdaq_daily_prices (symbol, date, open, high, low, close, volume, adj_close)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (symbol, date) DO UPDATE SET
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                close=EXCLUDED.close, volume=EXCLUDED.volume, adj_close=EXCLUDED.adj_close
        """, rows, page_size=100)
        conn.commit()
        cur.close()

        log.info(f"  {symbol}: {len(rows)} days, {halal_status} ({halal_reason})")
        return True

    except Exception as e:
        log.error(f"  {symbol}: {e}")
        conn.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description="Collect NASDAQ stock data")
    parser.add_argument("--universe", type=str, default="top50",
                        help="Stock universe: top50, nasdaq100, sp500")
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols")
    args = parser.parse_args()

    conn = get_conn()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        symbols = get_universe(args.universe)

    log.info(f"Collecting data for {len(symbols)} stocks...")

    success = 0
    failed = 0
    halal_count = 0
    haram_count = 0

    for i, symbol in enumerate(symbols, 1):
        if collect_stock(conn, symbol):
            success += 1
        else:
            failed += 1

        if i % 10 == 0:
            log.info(f"  Progress: {i}/{len(symbols)}")

        time.sleep(YF_DELAY)

    # Count halal/haram
    cur = conn.cursor()
    cur.execute("SELECT halal_status, COUNT(*) FROM nasdaq_stocks GROUP BY halal_status")
    for row in cur.fetchall():
        if row["halal_status"] == "HALAL":
            halal_count = row["count"]
        elif row["halal_status"] == "HARAM":
            haram_count = row["count"]
    cur.close()

    conn.close()
    log.info(f"\nDone. {success} collected, {failed} failed")
    log.info(f"Halal: {halal_count}, Haram: {haram_count}")


if __name__ == "__main__":
    main()
