"""yfinance market data wrapper — lazy, non-fatal."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Country → benchmark ticker
_BENCHMARKS = {
    "USA": "^GSPC",
    "UK": "^FTSE",
    "Pakistan": "KSE100.KA",
    "India": "^BSESN",
    "UAE": "^ABUDHABI",
}

_DEFAULT_SUMMARY = {
    "trend": "neutral",
    "sp500_ytd": 0.0,
    "recommendation_basis": "Market data unavailable — using conservative estimates",
}


def get_market_summary(country: str = "USA") -> Dict:
    """Return market summary dict. Falls back to static defaults on failure."""
    from app.core.config import settings

    if not settings.YAHOO_FINANCE_ENABLED:
        return _DEFAULT_SUMMARY

    try:
        import yfinance as yf

        ticker_sym = _BENCHMARKS.get(country, "^GSPC")
        ticker = yf.Ticker(ticker_sym)
        hist = ticker.history(period="ytd")

        if hist.empty:
            return _DEFAULT_SUMMARY

        start_price = hist["Close"].iloc[0]
        end_price = hist["Close"].iloc[-1]
        ytd_change = ((end_price - start_price) / start_price) * 100

        trend = "bullish" if ytd_change > 3 else ("bearish" if ytd_change < -3 else "neutral")

        return {
            "trend": trend,
            "sp500_ytd": round(ytd_change, 2),
            "recommendation_basis": f"{country} market is {trend} ({ytd_change:+.1f}% YTD)",
        }
    except Exception as exc:
        logger.warning("Market data fetch failed: %s", exc)
        return _DEFAULT_SUMMARY


def get_stock_info(symbol: str) -> Optional[Dict]:
    """Return basic stock info or None on failure."""
    try:
        import yfinance as yf

        t = yf.Ticker(symbol)
        info = t.info
        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "sector": info.get("sector", "Unknown"),
            "pe_ratio": info.get("trailingPE"),
            "debt_to_equity": info.get("debtToEquity"),
        }
    except Exception as exc:
        logger.warning("Stock info failed for %s: %s", symbol, exc)
        return None
