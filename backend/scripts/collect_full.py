#!/usr/bin/env python3
"""
Collect FULL S&P 500 + NASDAQ 100 + popular stocks.
Uses yfinance to get the actual S&P 500 list and downloads everything.
"""

import sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)

from config import DATABASE_URL, HARAM_INDUSTRIES, HARAM_TICKERS, HALAL_MAX_DEBT_RATIO

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    log.error("Install: pip install yfinance pandas")
    sys.exit(1)


def get_sp500():
    """Get S&P 500 symbols from Wikipedia."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        symbols = tables[0]["Symbol"].str.replace(".", "-").tolist()
        log.info(f"S&P 500: {len(symbols)} symbols from Wikipedia")
        return symbols
    except Exception as e:
        log.warning(f"Wikipedia S&P 500 failed: {e}")
        return []


def get_nasdaq100():
    """Get NASDAQ 100 symbols."""
    try:
        tables = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        for t in tables:
            if "Ticker" in t.columns:
                symbols = t["Ticker"].tolist()
                log.info(f"NASDAQ 100: {len(symbols)} symbols")
                return symbols
            if "Symbol" in t.columns:
                symbols = t["Symbol"].tolist()
                log.info(f"NASDAQ 100: {len(symbols)} symbols")
                return symbols
    except Exception as e:
        log.warning(f"Wikipedia NASDAQ 100 failed: {e}")
    return []


def get_popular_extras():
    """Additional popular/trending stocks not in S&P 500."""
    return [
        # Photonics
        "LITE", "COHR", "IPGP",
        # Quantum
        "IONQ", "RGTI", "QBTS",
        # AI/ML smaller
        "PLTR", "AI", "BBAI", "SOUN", "BIGC",
        # Fintech
        "SOFI", "AFRM", "UPST", "HOOD",
        # EV
        "RIVN", "LCID", "NIO", "XPEV", "LI",
        # Crypto related
        "COIN", "MARA", "RIOT", "MSTR",
        # Biotech
        "MRNA", "BNTX", "CRSP", "NTLA", "BEAM",
        # Gaming
        "RBLX", "U", "TTWO",
        # Cloud/SaaS
        "SNOW", "MDB", "DDOG", "ZS", "CRWD", "NET", "CFLT",
        # Consumer
        "ABNB", "DASH", "UBER", "LYFT", "SHOP", "ETSY", "PINS",
        # Solar/Clean energy
        "ENPH", "SEDG", "FSLR", "RUN",
        # Space
        "RKLB",
        # Semiconductor
        "ARM", "SMCI", "ASML", "TSM",
        # Steel/Materials
        "CMC", "STLD", "NUE", "CLF",
    ]


def screen_halal(info, symbol):
    if symbol in HARAM_TICKERS:
        return "HARAM", f"Explicitly excluded"

    industry = info.get("industry", "") or ""
    sector = info.get("sector", "") or ""

    if industry in HARAM_INDUSTRIES:
        return "HARAM", f"Haram industry: {industry}"

    if sector == "Financial Services":
        if any(x in industry.lower() for x in ["bank", "insurance", "credit", "mortgage"]):
            return "HARAM", f"Financial: {industry}"

    market_cap = info.get("marketCap", 0) or 0
    total_debt = info.get("totalDebt", 0) or 0
    if market_cap > 0 and total_debt > 0:
        if total_debt / market_cap > HALAL_MAX_DEBT_RATIO:
            return "DOUBTFUL", f"Debt/MCap = {total_debt/market_cap:.0%} > 33%"

    return "HALAL", "Passes all screens"


def collect_stock(conn, symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or "regularMarketPrice" not in info:
            return False

        halal_status, halal_reason = screen_halal(info, symbol)

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
            symbol, info.get("longName") or info.get("shortName"),
            info.get("sector"), info.get("industry"),
            info.get("marketCap"), info.get("trailingPE"), info.get("trailingEps"),
            info.get("dividendYield"), info.get("debtToEquity"),
            (info.get("totalDebt", 0) or 0) / max(info.get("marketCap", 1), 1),
            info.get("totalRevenue"), info.get("netIncomeToCommon"),
            info.get("freeCashflow"), info.get("beta"),
            info.get("averageVolume"), info.get("fiftyTwoWeekHigh"), info.get("fiftyTwoWeekLow"),
            halal_status, halal_reason,
        ))
        conn.commit()

        # Price history (2 years)
        hist = ticker.history(period="2y", interval="1d")
        if hist.empty:
            cur.close()
            return True

        rows = []
        for dt, row in hist.iterrows():
            rows.append((
                symbol, dt.date(),
                round(float(row["Open"]), 4), round(float(row["High"]), 4),
                round(float(row["Low"]), 4), round(float(row["Close"]), 4),
                int(row["Volume"]),
                round(float(row["Close"]), 4),
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
        return True

    except Exception as e:
        conn.rollback()
        return False


def main():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)

    # Combine all universes, deduplicate
    sp500 = get_sp500()
    nasdaq100 = get_nasdaq100()
    extras = get_popular_extras()

    all_symbols = sorted(set(sp500 + nasdaq100 + extras))
    log.info(f"Total unique symbols: {len(all_symbols)}")

    # Check which we already have
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM nasdaq_stocks")
    existing = {r["symbol"] for r in cur.fetchall()}
    cur.close()

    new_symbols = [s for s in all_symbols if s not in existing]
    log.info(f"Already collected: {len(existing)}, New to collect: {len(new_symbols)}")

    success = 0
    failed = 0
    for i, symbol in enumerate(new_symbols, 1):
        ok = collect_stock(conn, symbol)
        if ok:
            success += 1
        else:
            failed += 1

        if i % 25 == 0:
            log.info(f"  Progress: {i}/{len(new_symbols)} (success={success}, fail={failed})")

        time.sleep(0.3)

    # Final stats
    cur = conn.cursor()
    cur.execute("SELECT halal_status, COUNT(*) as cnt FROM nasdaq_stocks GROUP BY halal_status ORDER BY cnt DESC")
    stats = cur.fetchall()
    cur.execute("SELECT COUNT(DISTINCT symbol) as symbols, COUNT(*) as rows FROM nasdaq_daily_prices")
    price_stats = cur.fetchone()
    cur.close()
    conn.close()

    log.info(f"\nDone. New: {success} collected, {failed} failed")
    log.info(f"Total stocks in DB: {sum(r['cnt'] for r in stats)}")
    for r in stats:
        log.info(f"  {r['halal_status']}: {r['cnt']}")
    log.info(f"Price data: {price_stats['symbols']} stocks, {price_stats['rows']} rows")


if __name__ == "__main__":
    main()
