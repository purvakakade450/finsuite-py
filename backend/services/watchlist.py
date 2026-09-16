"""Watchlist & Price Alerts — Day 14 equivalent of finsuite.html.

No separate storage needed: the watchlist itself (which symbols, which
alert thresholds) is kept in the browser by the frontend. This module's
only job is to safely fetch quotes for several symbols at once, reusing
market_data's cache + 25/day rate limiter so watching many symbols can
never blow the daily quota — symbols already cached this minute are
served from cache instead of making a fresh call.
"""
from . import market_data


def get_quotes(symbols: list[str]) -> list[dict]:
    """Fetch a quote for each symbol. Never raises for an individual
    failure — a bad symbol or an exhausted quota just gets an 'error'
    field on its own row so the rest of the watchlist still renders."""
    results = []
    for symbol in symbols:
        symbol = symbol.strip().upper()
        if not symbol:
            continue
        try:
            results.append(market_data.get_quote(symbol))
        except (market_data.RateLimitExceeded, market_data.MarketDataUnavailable) as e:
            results.append({"symbol": symbol, "error": str(e)})
    return results


def check_alerts(entries: list[dict]) -> list[dict]:
    """entries: [{"symbol", "price", "target_price", "condition"}, ...]
    condition is "above" or "below". Returns each entry with a
    "triggered" bool added, so the UI can highlight fired alerts."""
    out = []
    for e in entries:
        price = e.get("price")
        target = e.get("target_price")
        condition = e.get("condition", "above")
        triggered = False
        if price is not None and target is not None:
            triggered = price >= target if condition == "above" else price <= target
        out.append({**e, "triggered": triggered})
    return out