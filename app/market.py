"""
market.py
=========
Live stock market data with **NO API key, no signup, no environment
variable required** — everything runs off public, free endpoints:

  * Company/ticker search        -> Yahoo Finance search (via `yfinance`)
  * Quotes & daily OHLCV history -> `yfinance` (reads public Yahoo Finance data)
  * News headlines               -> Google News' public RSS feed

Any symbol Yahoo Finance lists works: NSE ("TATASTEEL.NS"), BSE
("500325.BO"), US ("AAPL"), indices ("^NSEI"), ETFs, etc. A bare Indian
ticker such as "TATASTEEL" is tried on NSE, then BSE, automatically.

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

import re

import logging

import requests
import yfinance as yf

# yfinance logs an error for every symbol it can't find; we try several
# candidates per lookup and report failures ourselves.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

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


def _to_yahoo_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol in _KNOWN_SYMBOLS:
        return _KNOWN_SYMBOLS[symbol]
    if symbol.endswith(".BSE"):
        return symbol[:-4] + ".NS"   # generic fallback for any other "XXX.BSE" symbol
    if symbol.endswith(".NSE"):
        return symbol[:-4] + ".NS"
    return symbol                     # Yahoo-style already, or a plain ticker ("IBM")


def _candidates(symbol: str) -> list[str]:
    """Yahoo symbols to try, in order. A bare ticker that isn't a US listing
    (e.g. "TATASTEEL") is retried on NSE and then BSE."""
    yahoo = _to_yahoo_symbol(symbol)
    if re.fullmatch(r"[A-Z0-9&-]+", yahoo):
        return [yahoo, yahoo + ".NS", yahoo + ".BO"]
    return [yahoo]


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


# --------------------------------------------------------------------------
# 0) COMPANY SEARCH  -- find the ticker for any company by name
# --------------------------------------------------------------------------
SEARCH_TTL = 60 * 60
NAME_TTL = 24 * 60 * 60
_SEARCH_TYPES = {"EQUITY", "ETF", "INDEX", "MUTUALFUND"}


def _exchange_rank(symbol: str) -> int:
    # India-first app: NSE listings, then BSE, then everything else;
    # "-BL"/"-BE" style block-deal series last.
    if "-" in symbol.split(".")[0]:
        return 3
    if symbol.endswith(".NS"):
        return 0
    if symbol.endswith(".BO"):
        return 1
    return 2


def search_symbols(query: str, limit: int = 8) -> list[dict]:
    """Companies/ETFs/indices matching `query` (a name or ticker).

    Returns:
        [{"symbol": "TATASTEEL.NS", "name": "Tata Steel Limited",
          "exchange": "NSE", "type": "EQUITY"}, ...]
    """
    query = query.strip()
    if not query:
        return []
    return _cached(f"search:{query.upper()}:{limit}", SEARCH_TTL,
                   lambda: _fetch_search(query, limit))


def _fetch_search(query: str, limit: int) -> list[dict]:
    raw = yf.Search(query, max_results=max(limit * 2, 10), news_count=0).quotes or []
    results = []
    for i, q in enumerate(raw):
        symbol = q.get("symbol")
        if not symbol or q.get("quoteType") not in _SEARCH_TYPES:
            continue
        results.append((_exchange_rank(symbol), i, {
            "symbol": symbol,
            "name": q.get("longname") or q.get("shortname") or symbol,
            "exchange": q.get("exchDisp") or q.get("exchange") or "",
            "type": q.get("quoteType"),
        }))
    # Keep Yahoo's relevance order, but float Indian listings above foreign
    # ones and push block-deal series to the end.
    results.sort(key=lambda r: (r[0] == 3, r[0] == 2, r[1]))
    return [r[2] for r in results[:limit]]


def company_name(symbol: str) -> str | None:
    """Full company name for a ticker, e.g. "HDFCBANK.NS" -> "HDFC Bank Limited"."""
    def fetch():
        for yahoo in _candidates(symbol):
            for q in yf.Search(yahoo, max_results=5, news_count=0).quotes or []:
                if (q.get("symbol") or "").upper() == yahoo:
                    return q.get("longname") or q.get("shortname")
        return None
    try:
        return _cached(f"name:{symbol.strip().upper()}", NAME_TTL, fetch)
    except Exception:
        return None


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


def _best_match(text: str) -> str | None:
    try:
        hits = search_symbols(text, limit=1)
    except Exception:
        return None
    return hits[0]["symbol"] if hits else None


def _resolve(symbol: str):
    """Yield Yahoo symbols to try for user input, best guess first.

    Company names ("samsung", "Tata Steel") go through Yahoo search first;
    ticker-looking input ("TATASTEEL", "AAPL") is tried directly first, with
    search as the last resort."""
    text = symbol.strip()
    is_name = " " in text or text != text.upper()
    tried = set()
    order = ([_best_match] if is_name else []) + [_candidates] + ([] if is_name else [_best_match])
    for source in order:
        found = source(text)
        for yahoo in ([found] if isinstance(found, str) else found or []):
            if yahoo and yahoo.upper() not in tried:
                tried.add(yahoo.upper())
                yield yahoo


_NOT_FOUND = ("No market data found for '{}'. Pick a company from the dropdown, or try its "
              "full name or ticker (e.g. TATASTEEL.NS for NSE, AAPL for US).")


def _fetch_quote(symbol: str) -> dict:
    for yahoo_symbol in _resolve(symbol):
        try:
            return _quote_for(symbol, yahoo_symbol)
        except ValueError:
            continue
    raise ValueError(_NOT_FOUND.format(symbol))


def _quote_for(symbol: str, yahoo_symbol: str) -> dict:
    ticker = yf.Ticker(yahoo_symbol)

    # Daily bars first: one request that also tells us whether the symbol
    # exists at all, so wrong guesses (e.g. bare "TATASTEEL") fail fast.
    daily = ticker.history(period="1mo")
    if daily.empty:
        raise ValueError(f"No quote data returned for {yahoo_symbol}.")
    currency = (ticker.history_metadata or {}).get("currency")
    last = daily.iloc[-1]
    price = float(last["Close"])
    prev_close = float(daily["Close"].iloc[-2]) if len(daily) > 1 else None
    day_open, day_high, day_low = float(last["Open"]), float(last["High"]), float(last["Low"])
    volume = int(last["Volume"])
    as_of = daily.index[-1].isoformat()

    # The latest session's 1-minute bars give the last traded price and the
    # actual time of that trade. A 5-day window means weekends/holidays
    # still return the most recent session.
    try:
        intraday = ticker.history(period="5d", interval="1m")
        if not intraday.empty:
            last_day = intraday.index[-1].date()
            if last_day > daily.index[-1].date():
                # daily bar for today not published yet: yesterday's close is prev close
                prev_close = price
            intraday = intraday[intraday.index.date == last_day]
            price = float(intraday["Close"].iloc[-1])
            day_open = float(intraday["Open"].iloc[0])
            day_high = float(intraday["High"].max())
            day_low = float(intraday["Low"].min())
            volume = max(volume, int(intraday["Volume"].sum())) if last_day == daily.index[-1].date() \
                else int(intraday["Volume"].sum())
            as_of = intraday.index[-1].isoformat()
    except Exception:
        pass

    change = (price - prev_close) if prev_close else None
    change_pct = (change / prev_close * 100) if prev_close else None
    return {
        "symbol": symbol,
        "yahooSymbol": yahoo_symbol,
        "name": company_name(yahoo_symbol) or yahoo_symbol,
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
    for yahoo_symbol in _resolve(symbol):
        hist = yf.Ticker(yahoo_symbol).history(period=period)
        if not hist.empty:
            break
    else:
        raise ValueError(_NOT_FOUND.format(symbol))

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

    `symbols` can be comma-separated tickers ("RELIANCE.NS,TCS.NS"), plain
    search text ("Reliance Industries"), or empty for general market news.

    Returns:
        [{"title": "...", "source": "...",
          "published_at": "2026-10-01T09:30:00+00:00", "link": "..."}, ...]
    """
    return _cached(f"news:{symbols.strip().upper()}:{limit}", NEWS_TTL,
                   lambda: _fetch_news(symbols, limit))


MARKET_NEWS_QUERY = '"stock market" (Sensex OR Nifty)'
_NAME_SUFFIX = re.compile(r"[\s,.]+(limited|ltd|inc|corp|corporation|co|plc|company)\.?$", re.I)


def _news_term(token: str) -> str:
    """Tickers become the company's name ("HDFCBANK.NS" -> "HDFC Bank"),
    which matches far more headlines than the bare ticker."""
    token = token.strip()
    looks_like_ticker = " " not in token and (token.isupper() or re.search(r"[.^=]", token))
    if not looks_like_ticker:
        return token                   # free-text query
    name = company_name(token)
    if name:
        while _NAME_SUFFIX.search(name):
            name = _NAME_SUFFIX.sub("", name)
        return f'"{name}"'
    base = _to_yahoo_symbol(token).split(".")[0].lstrip("^")
    return f"{base} share"             # unknown ticker: bias toward market coverage


def _fetch_news(symbols: str, limit: int) -> list[dict]:
    terms = [_news_term(t) for t in symbols.split(",") if t.strip()] or [MARKET_NEWS_QUERY]
    # `when:7d` restricts Google News to the last week so results stay current.
    query = " OR ".join(terms) + " when:7d"
    # Google News occasionally answers a valid query with a transient 404/5xx,
    # so retry a couple of times before giving up.
    for attempt in range(3):
        resp = requests.get(
            "https://news.google.com/rss/search",
            params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
            headers={"User-Agent": "Mozilla/5.0"},  # Google News RSS 403s with no UA
            timeout=10,
        )
        if resp.ok:
            break
        time.sleep(0.5 * (attempt + 1))
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
