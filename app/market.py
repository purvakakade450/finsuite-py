"""
market.py
=========
Live stock market data with **NO API key, no signup, no environment
variable required** — everything runs off public, free endpoints:

  * Quotes & daily OHLCV history -> `yfinance` (reads public Yahoo Finance data)
  * News headlines               -> Google News' public RSS feed

Responses are cached in memory for a short time (see the *_TTL constants)
so bursts of requests — e.g. a watchlist refresh — don't get throttled by
Yahoo. If a live call fails, the last good value is served instead.

Install once:
    pip install yfinance requests

Test it stand-alone (no server needed) with:
    python -m app.market RELIANCE.BSE
"""
from __future__ import annotations

import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
import yfinance as yf

# --------------------------------------------------------------------------
# Symbol translation: this app's UI uses "RELIANCE.BSE"-style symbols
# (a holdover from the old Alpha Vantage integration). Yahoo Finance /
# yfinance instead expects NSE tickers with a ".NS" suffix, which is both
# more reliable and more current than BSE data for Indian equities.
# --------------------------------------------------------------------------
_KNOWN_SYMBOLS = {
    "RELIANCE.BSE": "RELIANCE.NS",
    "TCS.BSE": "TCS.NS",
    "INFY.BSE": "INFY.NS",
}

# Company names give Google News far better matches than bare tickers.
_COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "INFY": "Infosys",
    "IBM": "IBM",
}


def _to_yahoo_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol in _KNOWN_SYMBOLS:
        return _KNOWN_SYMBOLS[symbol]
    if symbol.endswith(".BSE"):
        return symbol[:-4] + ".NS"   # generic fallback for any other "XXX.BSE" symbol
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol                 # already Yahoo-style
    return symbol                     # plain ticker, e.g. "IBM", "AAPL"


# --------------------------------------------------------------------------
# Tiny in-memory TTL cache
# --------------------------------------------------------------------------
QUOTE_TTL = 30          # seconds
HISTORY_TTL = 10 * 60
NEWS_TTL = 5 * 60

_cache: dict[str, tuple[float, object]] = {}
_cache_lock = threading.Lock()


def _cached(key: str, ttl: int, fetch):
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        value = fetch()
    except Exception:
        if hit:                      # serve the last good value if the live call fails
            return hit[1]
        raise
    with _cache_lock:
        _cache[key] = (now, value)
    return value


def _r(x):
    return round(float(x), 2) if x is not None else None


# --------------------------------------------------------------------------
# 1) LIVE QUOTE
# --------------------------------------------------------------------------
def get_quote(symbol: str) -> dict:
    """Current price snapshot for one symbol. No key required.

    Returns:
        {"symbol": "RELIANCE.BSE", "yahooSymbol": "RELIANCE.NS", "price": 2871.4,
         "change": 12.3, "changePercent": "0.43", "previousClose": 2859.1,
         "open": 2860.0, "dayHigh": 2880.0, "dayLow": 2850.2, "volume": 4821342,
         "currency": "INR", "asOf": "2026-10-01T15:29:00+05:30"}

    Raises:
        ValueError if Yahoo Finance has no data for the symbol (bad ticker,
        delisted, or a transient outage).
    """
    return _cached(f"quote:{symbol.strip().upper()}", QUOTE_TTL, lambda: _fetch_quote(symbol))


def _fetch_quote(symbol: str) -> dict:
    yahoo_symbol = _to_yahoo_symbol(symbol)
    ticker = yf.Ticker(yahoo_symbol)

    price = prev_close = currency = None
    try:
        info = ticker.fast_info
        price = info.get("last_price")
        prev_close = info.get("previous_close")
        currency = info.get("currency")
    except Exception:
        pass

    # The latest session's 1-minute bars give the last traded price, the
    # day's range and the actual time of that trade. A 5-day window means
    # weekends/holidays still return the most recent session.
    as_of = day_open = day_high = day_low = volume = None
    try:
        intraday = ticker.history(period="5d", interval="1m")
        if not intraday.empty:
            last_day = intraday.index[-1].date()
            intraday = intraday[intraday.index.date == last_day]
            price = float(intraday["Close"].iloc[-1])
            day_open = float(intraday["Open"].iloc[0])
            day_high = float(intraday["High"].max())
            day_low = float(intraday["Low"].min())
            volume = int(intraday["Volume"].sum())
            as_of = intraday.index[-1].isoformat()
    except Exception:
        pass

    # fast_info is occasionally empty right after Yahoo rate-limits a burst
    # of requests -- fall back to recent daily history.
    if price is None or prev_close is None:
        hist = ticker.history(period="5d")
        if not hist.empty:
            if price is None:
                price = float(hist["Close"].iloc[-1])
                as_of = hist.index[-1].isoformat()
            if prev_close is None and len(hist) > 1:
                prev_close = float(hist["Close"].iloc[-2])

    if price is None:
        raise ValueError(f"No quote data returned for {symbol} ({yahoo_symbol}). "
                          f"Check the symbol is correct, or try again in a moment.")

    change = (price - prev_close) if prev_close else None
    change_pct = (change / prev_close * 100) if prev_close else None
    return {
        "symbol": symbol,
        "yahooSymbol": yahoo_symbol,
        "price": _r(price),
        "change": _r(change),
        "changePercent": f"{change_pct:.2f}" if change_pct is not None else None,
        "previousClose": _r(prev_close),
        "open": _r(day_open),
        "dayHigh": _r(day_high),
        "dayLow": _r(day_low),
        "volume": volume,
        "currency": currency or ("INR" if yahoo_symbol.endswith((".NS", ".BO")) else "USD"),
        "asOf": as_of,
    }


# --------------------------------------------------------------------------
# 2) DAILY OHLCV HISTORY
# --------------------------------------------------------------------------
def get_daily_history(symbol: str, period: str = "3mo") -> list[dict]:
    """Real daily Open/High/Low/Close/Volume history. No key required.

    `period` accepts yfinance's usual strings: "1mo", "3mo", "6mo", "1y",
    "2y", "5y", "max", etc.

    Returns a list of row dicts, oldest first:
        [{"Date": "2026-06-01", "Open": 2850.0, "High": 2870.5,
          "Low": 2845.0, "Close": 2865.3, "Volume": 4821342}, ...]
    """
    return _cached(f"history:{symbol.strip().upper()}:{period}", HISTORY_TTL,
                   lambda: _fetch_history(symbol, period))


def _fetch_history(symbol: str, period: str) -> list[dict]:
    yahoo_symbol = _to_yahoo_symbol(symbol)
    hist = yf.Ticker(yahoo_symbol).history(period=period)
    if hist.empty:
        raise ValueError(f"No history returned for {symbol} ({yahoo_symbol}). "
                          f"Check the symbol is correct, or try again in a moment.")

    rows = []
    for idx, row in hist.iterrows():
        rows.append({
            "Date": idx.strftime("%Y-%m-%d"),
            "Open": round(float(row["Open"]), 2),
            "High": round(float(row["High"]), 2),
            "Low": round(float(row["Low"]), 2),
            "Close": round(float(row["Close"]), 2),
            "Volume": int(row["Volume"]),
        })
    return rows


# --------------------------------------------------------------------------
# 3) NEWS HEADLINES  (Google News public RSS -- no key)
# --------------------------------------------------------------------------
def get_news(symbols: str, limit: int = 10) -> list[dict]:
    """Recent headlines (last 7 days) for the given symbols/query, newest first.

    `symbols` can be comma-separated tickers ("RELIANCE.BSE,TCS.BSE") or
    plain search text ("Reliance Industries").

    Returns:
        [{"title": "...", "source": "...",
          "published_at": "2026-10-01T09:30:00+00:00", "link": "..."}, ...]
    """
    return _cached(f"news:{symbols.strip().upper()}:{limit}", NEWS_TTL,
                   lambda: _fetch_news(symbols, limit))


def _news_term(token: str) -> str:
    token = token.strip()
    base = token.upper().split(".")[0]
    if base in _COMPANY_NAMES:
        return f'"{_COMPANY_NAMES[base]}"'
    if "." in token or (token.isupper() and " " not in token):
        return f"{base} share"         # unknown ticker: bias toward market coverage
    return token                       # free-text query


def _fetch_news(symbols: str, limit: int) -> list[dict]:
    terms = [_news_term(t) for t in symbols.split(",") if t.strip()]
    if not terms:
        raise ValueError("Enter at least one symbol or search term.")
    # `when:7d` restricts Google News to the last week so results stay current.
    query = " OR ".join(terms) + " when:7d"
    resp = requests.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        headers={"User-Agent": "Mozilla/5.0"},  # Google News RSS 403s with no UA
        timeout=10,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    items = []
    for item in root.findall("./channel/item"):
        source = (item.findtext("source") or "").strip()
        title = (item.findtext("title") or "").strip()
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]   # Google appends " - Source" to titles
        try:
            published = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            published = None
        items.append((published or datetime.min.replace(tzinfo=timezone.utc), {
            "title": title,
            "source": source,
            "published_at": published.isoformat() if published else "",
            "link": (item.findtext("link") or "").strip(),
        }))

    items.sort(key=lambda pair: pair[0], reverse=True)
    return [article for _, article in items[:limit]]


# --------------------------------------------------------------------------
# Stand-alone test -- run `python -m app.market [SYMBOL]` to sanity-check
# this file works BEFORE wiring it into the FastAPI app.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE.BSE"

    print(f"--- Quote for {symbol} ---")
    try:
        print(get_quote(symbol))
    except Exception as e:
        print("FAILED:", e)

    print(f"\n--- Last 5 days of history for {symbol} ---")
    try:
        for row in get_daily_history(symbol, period="1mo")[-5:]:
            print(row)
    except Exception as e:
        print("FAILED:", e)

    print(f"\n--- News for {symbol} ---")
    try:
        for article in get_news(symbol, limit=5):
            print("-", article["published_at"][:16], article["title"])
    except Exception as e:
        print("FAILED:", e)
