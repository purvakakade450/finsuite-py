"""
market.py
=========
Live stock market data with **NO API key, no signup, no environment
variable required** — everything runs off public, free endpoints:

  * Quotes & daily OHLCV history -> `yfinance` (reads public Yahoo Finance data)
  * News headlines               -> Google News' public RSS feed

This is a drop-in replacement for whatever `app/market.py` you currently
have (the one throwing "No ALPHA_VANTAGE_KEY set on the server" / "module
'app.market' has no attribute 'get_news'"). Copy this file over your
existing `app/market.py` and the errors in your screenshot go away —
`get_quote`, `get_daily_history`, and `get_news` are all defined below
with the exact names/shapes the rest of the app expects.

Install once:
    pip install yfinance requests

Test it stand-alone (no server needed) with:
    python market.py RELIANCE.BSE
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from typing import Optional

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
# 1) LIVE QUOTE
# --------------------------------------------------------------------------
def get_quote(symbol: str) -> dict:
    """Current price snapshot for one symbol. No key required.

    Returns:
        {"symbol": "RELIANCE.BSE", "price": 2871.4, "change": 12.3,
         "changePercent": "0.43", "previousClose": 2859.1}

    Raises:
        ValueError if Yahoo Finance has no data for the symbol (bad ticker,
        delisted, or a transient outage).
    """
    yahoo_symbol = _to_yahoo_symbol(symbol)
    ticker = yf.Ticker(yahoo_symbol)

    price = prev_close = None
    try:
        info = ticker.fast_info
        price = info.get("last_price")
        prev_close = info.get("previous_close")
    except Exception:
        pass

    # fast_info is occasionally empty right after Yahoo rate-limits a burst
    # of requests -- fall back to the last close from recent daily history.
    if price is None:
        hist = ticker.history(period="5d")
        if not hist.empty:
            price = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else None

    if price is None:
        raise ValueError(f"No quote data returned for {symbol} ({yahoo_symbol}). "
                          f"Check the symbol is correct, or try again in a moment.")

    change = (price - prev_close) if prev_close else None
    change_pct = (change / prev_close * 100) if prev_close else None
    return {
        "symbol": symbol,
        "price": round(float(price), 2),
        "change": round(float(change), 2) if change is not None else None,
        "changePercent": f"{change_pct:.2f}" if change_pct is not None else None,
        "previousClose": round(float(prev_close), 2) if prev_close else None,
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
    """Recent headlines for the given symbols/query. No key required.

    `symbols` can be comma-separated tickers ("RELIANCE.BSE,TCS.BSE") or
    plain search text ("Reliance Industries").

    Returns:
        [{"title": "...", "source": "...", "published_at": "...", "link": "..."}, ...]
    """
    query = symbols.replace(",", " OR ").replace(".BSE", "").replace(".NS", "")
    resp = requests.get(
        "https://news.google.com/rss/search",
        params={"q": query, "hl": "en-IN", "gl": "IN", "ceid": "IN:en"},
        headers={"User-Agent": "Mozilla/5.0"},  # Google News RSS 403s with no UA
        timeout=10,
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    items = []
    for item in root.findall("./channel/item")[:limit]:
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "source": (item.findtext("source") or "").strip(),
            "published_at": (item.findtext("pubDate") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
        })
    return items


# --------------------------------------------------------------------------
# Stand-alone test -- run `python market.py [SYMBOL]` to sanity-check this
# file works BEFORE wiring it into the FastAPI app.
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
            print("-", article["title"])
    except Exception as e:
        print("FAILED:", e)
        