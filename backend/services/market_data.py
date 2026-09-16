"""
Live market data via Alpha Vantage — fetched SERVER-SIDE.

Why server-side matters:
  1. No CORS problem: browsers block cross-origin calls from arbitrary
     pages, but a server calling another server has no such restriction.
  2. No exposed key: the API key lives in an environment variable on the
     server and is never sent to the browser.
  3. Rate-limit safety ("don't exceed limit"): Alpha Vantage's free tier
     allows only 25 requests/day. This module tracks how many calls have
     been made today and caches every response, so the SAME symbol is
     never re-fetched more than once inside its cache window, and once
     the daily quota is used up we serve the last cached value instead
     of erroring.
"""
import os
import time
import threading
from datetime import date

import requests

ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"
DAILY_REQUEST_LIMIT = 25          # Alpha Vantage free-tier cap
QUOTE_CACHE_TTL_SECONDS = 60      # don't re-hit the API more than once/min per symbol
HISTORY_CACHE_TTL_SECONDS = 60 * 60 * 6   # daily history barely changes intraday

_lock = threading.Lock()
_cache: dict[str, dict] = {}          # key -> {"data": ..., "ts": float}
_request_log: dict[str, int] = {}     # "YYYY-MM-DD" -> count


class RateLimitExceeded(Exception):
    pass


class MarketDataUnavailable(Exception):
    pass


def _today_key() -> str:
    return date.today().isoformat()


def calls_made_today() -> int:
    with _lock:
        return _request_log.get(_today_key(), 0)


def calls_remaining_today() -> int:
    return max(0, DAILY_REQUEST_LIMIT - calls_made_today())


def _register_call():
    with _lock:
        k = _today_key()
        _request_log[k] = _request_log.get(k, 0) + 1


def _get_cached(cache_key: str, ttl: int):
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry["ts"]) < ttl:
        return entry["data"], True
    return entry["data"] if entry else None, False


def _set_cached(cache_key: str, data):
    _cache[cache_key] = {"data": data, "ts": time.time()}


def _call_alpha_vantage(params: dict) -> dict:
    if not ALPHA_VANTAGE_KEY:
        raise MarketDataUnavailable(
            "No ALPHA_VANTAGE_KEY set on the server. Set it as an environment "
            "variable, or use the /api/simulate endpoint for practice data instead."
        )
    if calls_remaining_today() <= 0:
        raise RateLimitExceeded(
            f"Daily Alpha Vantage limit of {DAILY_REQUEST_LIMIT} requests reached. "
            "Serving the last cached value instead, if one exists."
        )
    resp = requests.get(
        ALPHA_VANTAGE_URL,
        params={**params, "apikey": ALPHA_VANTAGE_KEY},
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    if "Note" in payload or "Information" in payload:
        # Alpha Vantage returns HTTP 200 with a "Note"/"Information" field
        # when you're rate limited, instead of a real HTTP error.
        raise RateLimitExceeded(payload.get("Note") or payload.get("Information"))
    if "Error Message" in payload:
        raise MarketDataUnavailable(payload["Error Message"])
    _register_call()
    return payload


def get_quote(symbol: str) -> dict:
    """Current price snapshot for one symbol. Cached for QUOTE_CACHE_TTL_SECONDS."""
    cache_key = f"quote:{symbol}"
    cached, fresh = _get_cached(cache_key, QUOTE_CACHE_TTL_SECONDS)
    if fresh:
        return {**cached, "source": "cache"}

    try:
        payload = _call_alpha_vantage({"function": "GLOBAL_QUOTE", "symbol": symbol})
    except (RateLimitExceeded, MarketDataUnavailable):
        if cached is not None:
            return {**cached, "source": "stale-cache"}
        raise

    quote = payload.get("Global Quote") or {}
    if not quote:
        raise MarketDataUnavailable(f"No quote data returned for {symbol}.")
    data = {
        "symbol": symbol,
        "price": float(quote.get("05. price", 0)),
        "change": float(quote.get("09. change", 0)),
        "changePercent": quote.get("10. change percent", "0%").strip("%"),
        "previousClose": float(quote.get("08. previous close", 0)),
        "latestTradingDay": quote.get("07. latest trading day", ""),
    }
    _set_cached(cache_key, data)
    return {**data, "source": "live"}


def get_daily_history(symbol: str, outputsize: str = "compact") -> list[dict]:
    """Real daily OHLCV history. Cached for HISTORY_CACHE_TTL_SECONDS."""
    cache_key = f"history:{symbol}:{outputsize}"
    cached, fresh = _get_cached(cache_key, HISTORY_CACHE_TTL_SECONDS)
    if fresh:
        return cached

    try:
        payload = _call_alpha_vantage({
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
        })
    except (RateLimitExceeded, MarketDataUnavailable):
        if cached is not None:
            return cached
        raise

    series = payload.get("Time Series (Daily)") or {}
    rows = []
    for d, vals in sorted(series.items()):
        rows.append({
            "Date": d,
            "Open": float(vals["1. open"]),
            "High": float(vals["2. high"]),
            "Low": float(vals["3. low"]),
            "Close": float(vals["4. close"]),
            "Volume": int(vals["5. volume"]),
        })
    _set_cached(cache_key, rows)
    return rows
