"""NASDAQ Trading System Configuration."""

import os

# Database — same PostgreSQL, nasdaq_ prefixed tables
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:dse_local_2026@127.0.0.1:5432/dse_trading",
)

# Yahoo Finance settings
YF_MAX_RETRIES = 3
YF_DELAY = 0.5  # seconds between requests

# Halal screening thresholds
HALAL_MAX_DEBT_RATIO = 0.33  # debt/market_cap < 33%
HALAL_MAX_HARAM_REVENUE = 0.05  # < 5% haram revenue

# Haram sectors/industries to exclude
HARAM_INDUSTRIES = {
    "Alcoholic Beverages", "Brewers", "Distillers & Vintners", "Wineries & Distilleries",
    "Tobacco", "Gambling", "Casinos & Gaming",
    "Banks—Diversified", "Banks—Regional", "Credit Services",
    "Insurance—Diversified", "Insurance—Life", "Insurance—Property & Casualty",
    "Insurance Brokers", "Mortgage Finance",
    "Aerospace & Defense",  # weapons
    "Entertainment",  # some are haram (adult content)
}

# Haram stocks explicitly (even if industry seems fine)
HARAM_TICKERS = {
    "BUD", "DEO", "STZ", "TAP", "SAM",  # alcohol
    "PM", "MO", "BTI",  # tobacco
    "DKNG", "MGM", "WYNN", "LVS", "CZR",  # gambling
    "LMT", "RTX", "NOC", "GD", "BA",  # weapons (debatable for BA)
    "JPM", "BAC", "WFC", "C", "GS", "MS",  # banks
    "AIG", "MET", "PRU", "ALL",  # insurance
}

# API settings
API_PREFIX = "/api/v1"
CORS_ORIGINS = ["*"]
PORT = 8001  # different from DSE backend (8000)
