"""
Chart and news analysis on top of the live data in market.py:
technical indicators (moving averages, Bollinger bands, RSI), a two-stock
comparison, and a word-list sentiment score for news headlines.
"""
from __future__ import annotations

import math
import re

import pandas as pd

from backend.services.features import _rsi
from . import market

# Extra history fetched before the requested period so 50-day averages and
# RSI already have values on the first visible day.
_WARMUP = {"1mo": "6mo", "3mo": "1y", "6mo": "1y", "1y": "2y", "2y": "5y", "5y": "max", "max": "max"}
_DAYS = {"1mo": 31, "3mo": 92, "6mo": 183, "1y": 366, "2y": 731, "5y": 1827}


def _clean(series: pd.Series) -> list:
    return [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), 2)
            for v in series]


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------
def get_indicators(symbol: str, period: str = "6mo") -> dict:
    raw = market.get_history(symbol, _WARMUP[period])
    df = pd.DataFrame(raw["rows"]).dropna(subset=["Close"]).reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No history for {symbol}")
    close = df["Close"]
    df["SMA20"] = close.rolling(20).mean()
    df["SMA50"] = close.rolling(50).mean()
    df["EMA20"] = close.ewm(span=20, adjust=False).mean()
    std = close.rolling(20).std()
    df["BB_upper"] = df["SMA20"] + 2 * std
    df["BB_lower"] = df["SMA20"] - 2 * std
    df["RSI14"] = _rsi(close, 14)
    if period in _DAYS:
        start = pd.Timestamp(df["Date"].iloc[-1]) - pd.Timedelta(days=_DAYS[period])
        df = df[pd.to_datetime(df["Date"]) >= start]

    last = df.iloc[-1]
    rsi = last["RSI14"]
    signals = []
    if not math.isnan(rsi):
        signals.append(f"RSI is {rsi:.0f}: " + (
            "above 70, the stock looks overbought (it has risen fast and may cool off)." if rsi > 70 else
            "below 30, the stock looks oversold (it has fallen fast and may bounce)." if rsi < 30 else
            "between 30 and 70, a neutral zone."))
    if not math.isnan(last["SMA50"]):
        above = last["Close"] > last["SMA50"]
        signals.append(f"Price is {'above' if above else 'below'} its 50-day average, "
                       f"a sign of a {'rising' if above else 'falling'} medium-term trend.")
    if not math.isnan(last["SMA20"]) and not math.isnan(last["SMA50"]):
        signals.append("The 20-day average is " + ("above" if last["SMA20"] > last["SMA50"] else "below") +
                       " the 50-day average (" + ("short-term momentum is up)." if last["SMA20"] > last["SMA50"]
                                                  else "short-term momentum is down)."))
    if not math.isnan(last["BB_upper"]):
        if last["Close"] > last["BB_upper"]:
            signals.append("Price closed above the upper Bollinger band: unusually high versus the last 20 days.")
        elif last["Close"] < last["BB_lower"]:
            signals.append("Price closed below the lower Bollinger band: unusually low versus the last 20 days.")
        else:
            signals.append("Price is inside its Bollinger bands, a normal range for the last 20 days.")

    return {
        "symbol": symbol, "yahooSymbol": raw["yahooSymbol"], "name": raw["name"], "currency": raw["currency"],
        "dates": df["Date"].tolist(), "close": _clean(df["Close"]),
        **{k.lower(): _clean(df[k]) for k in ("SMA20", "SMA50", "EMA20", "BB_upper", "BB_lower", "RSI14")},
        "latest": {"close": round(float(last["Close"]), 2),
                   "rsi14": None if math.isnan(rsi) else round(float(rsi), 1)},
        "signals": signals,
    }


# ---------------------------------------------------------------------------
# Compare two stocks
# ---------------------------------------------------------------------------
def _stats(closes: pd.Series) -> dict:
    rets = closes.pct_change().dropna()
    peak = closes.cummax()
    return {
        "start": round(float(closes.iloc[0]), 2), "end": round(float(closes.iloc[-1]), 2),
        "return_pct": round(float((closes.iloc[-1] / closes.iloc[0] - 1) * 100), 2),
        "volatility_pct": round(float(rets.std() * math.sqrt(252) * 100), 2) if len(rets) > 1 else 0.0,
        "max_drawdown_pct": round(float(((closes - peak) / peak).min() * 100), 2),
        "best_day_pct": round(float(rets.max() * 100), 2) if len(rets) else 0.0,
        "worst_day_pct": round(float(rets.min() * 100), 2) if len(rets) else 0.0,
    }


def compare_stocks(symbol_a: str, symbol_b: str, period: str = "1y") -> dict:
    a, b = market.get_history(symbol_a, period), market.get_history(symbol_b, period)
    sa = pd.Series({r["Date"]: r["Close"] for r in a["rows"]})
    sb = pd.Series({r["Date"]: r["Close"] for r in b["rows"]})
    both = pd.concat([sa, sb], axis=1, join="inner").dropna().sort_index()
    if len(both) < 2:
        raise ValueError("The two stocks have no overlapping trading days in this period.")
    ca, cb = both[0], both[1]
    corr = ca.pct_change().corr(cb.pct_change())
    stats_a, stats_b = _stats(ca), _stats(cb)
    winner = a if stats_a["return_pct"] >= stats_b["return_pct"] else b
    gap = abs(stats_a["return_pct"] - stats_b["return_pct"])
    corr_text = ("are very closely linked" if corr > 0.7 else "usually go the same way" if corr > 0.3
                 else "are mostly independent" if corr > -0.3 else "usually go opposite ways")
    summary = (f"{winner['name']} did better by {gap:.1f} percentage points over this period. "
               f"Their daily moves {corr_text} (correlation {corr:.2f}).")
    calmer = a if stats_a["volatility_pct"] <= stats_b["volatility_pct"] else b
    summary += f" {calmer['name']} was the steadier of the two (lower volatility)."
    return {
        "dates": both.index.tolist(),
        "a": {"symbol": a["yahooSymbol"], "name": a["name"], "currency": a["currency"],
              "rebased": _clean(ca / ca.iloc[0] * 100), "close": _clean(ca), **stats_a},
        "b": {"symbol": b["yahooSymbol"], "name": b["name"], "currency": b["currency"],
              "rebased": _clean(cb / cb.iloc[0] * 100), "close": _clean(cb), **stats_b},
        "correlation": None if math.isnan(corr) else round(float(corr), 2),
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# News sentiment (word list, no API key)
# ---------------------------------------------------------------------------
# Small finance-specific word lists in the spirit of the Loughran-McDonald
# dictionary: general-purpose sentiment words often mislead on headlines
# ("tax", "liability" are neutral in finance), so these are tuned to how
# market news is written.
POSITIVE = """
gain gains gained rise rises rising rose jump jumps jumped surge surges surged soar soars soared
rally rallies rallied climb climbs climbed up upgrade upgrades upgraded beat beats outperform outperforms
record high highs profit profits profitable growth grows grew strong stronger strongest robust boost boosts
boosted expand expands expansion bullish buy optimism optimistic positive recover recovers recovery rebound
rebounds rebounded win wins won award awarded approval approves approved dividend bonus milestone
breakthrough top tops upbeat success successful best gainers advance advances advanced higher increase
increased increases accelerate launch launches partnership deal order orders inflow inflows
""".split()
NEGATIVE = """
fall falls fell falling drop drops dropped decline declines declined slump slumps slumped plunge plunges
plunged crash crashes crashed tumble tumbles tumbled sink sinks sank slide slides slid down downgrade
downgrades downgraded miss misses missed loss losses lose loses lost weak weaker weakest bearish sell
selloff sell-off pessimism negative concern concerns worry worries fear fears risk risks warning warns
warned layoff layoffs fraud probe penalty fined lawsuit default defaults debt-laden scam
low lows lower slowdown slow slower slump crisis volatile volatility pressure outflow outflows halt halted
ban banned resign resigns resigned decrease decreased decreases underperform underperforms losers
""".split()
_NEGATORS = {"not", "no", "never", "without", "fails", "failed"}
_POS, _NEG = set(POSITIVE), set(NEGATIVE)


def headline_sentiment(text: str) -> dict:
    words = re.findall(r"[a-z][a-z\-]*", text.lower())
    pos, neg, hits = 0, 0, []
    for i, w in enumerate(words):
        flip = i > 0 and words[i - 1] in _NEGATORS
        if w in _POS:
            pos, neg = (pos, neg + 1) if flip else (pos + 1, neg)
            hits.append(w)
        elif w in _NEG:
            pos, neg = (pos + 1, neg) if flip else (pos, neg + 1)
            hits.append(w)
    score = (pos - neg) / (pos + neg) if pos + neg else 0.0
    label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
    return {"label": label, "score": round(score, 2), "words": hits}


def news_with_sentiment(symbols: str, limit: int = 10) -> dict:
    items = [{**a, "sentiment": headline_sentiment(a["title"])} for a in market.get_news(symbols, limit)]
    counts = {k: sum(a["sentiment"]["label"] == k for a in items) for k in ("positive", "neutral", "negative")}
    avg = sum(a["sentiment"]["score"] for a in items) / len(items) if items else 0.0
    mood = "positive" if avg > 0.15 else "negative" if avg < -0.15 else "mixed / neutral"
    return {"data": items, "summary": {**counts, "average_score": round(avg, 2), "mood": mood}}
