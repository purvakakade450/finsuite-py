"""Indicators, comparison, sentiment, mutual funds and the portfolio tracker,
all run on made-up prices so they need no internet."""
import math
from datetime import date, timedelta

import pytest

from app import analysis, market, mf, tracker


def _rows(n=320, start=100.0, drift=0.0005, wiggle=0.01, first=date(2025, 1, 1)):
    rows, price, d = [], start, first
    for i in range(n):
        while d.weekday() >= 5:
            d += timedelta(days=1)
        price *= 1 + drift + wiggle * math.sin(i / 3)
        rows.append({"Date": d.isoformat(), "Open": price, "High": price * 1.01, "Low": price * 0.99,
                     "Close": round(price, 2), "Volume": 1000 + i})
        d += timedelta(days=1)
    return rows


def _history(symbol, period="1y", **kw):
    return {"yahooSymbol": symbol, "name": f"{symbol} Ltd", "currency": "INR", "rows": _rows(**kw)}


@pytest.fixture()
def fake_history(monkeypatch):
    monkeypatch.setattr(market, "get_history", lambda symbol, period="3mo": _history(
        symbol, start=100 if symbol == "AAA" else 50, drift=0.001 if symbol == "AAA" else 0.0001))


# --------------------------------------------------------------- indicators
def test_indicators_have_values_from_the_first_visible_day(fake_history):
    d = analysis.get_indicators("AAA", "3mo")
    assert len(d["dates"]) == len(d["close"]) == len(d["sma50"]) == len(d["rsi14"])
    assert d["sma50"][0] is not None            # warm-up history was fetched before the visible window
    assert all(0 <= v <= 100 for v in d["rsi14"] if v is not None)
    assert d["signals"]


def test_bollinger_bands_surround_the_average(fake_history):
    d = analysis.get_indicators("AAA", "6mo")
    for lo, mid, hi in zip(d["bb_lower"], d["sma20"], d["bb_upper"]):
        if mid is not None:
            assert lo <= mid <= hi


# ---------------------------------------------------------------- comparison
def test_compare_rebases_both_to_100_and_picks_a_winner(fake_history):
    d = analysis.compare_stocks("AAA", "BBB", "1y")
    assert d["a"]["rebased"][0] == pytest.approx(100) and d["b"]["rebased"][0] == pytest.approx(100)
    assert d["a"]["return_pct"] > d["b"]["return_pct"]
    assert "AAA Ltd did better" in d["summary"]
    assert -1 <= d["correlation"] <= 1
    assert d["a"]["max_drawdown_pct"] <= 0


def test_compare_with_no_overlap_is_a_clear_error(monkeypatch):
    monkeypatch.setattr(market, "get_history", lambda s, p="1y": _history(
        s, n=30, first=date(2020, 1, 1) if s == "AAA" else date(2024, 1, 1)))
    with pytest.raises(ValueError, match="overlapping"):
        analysis.compare_stocks("AAA", "BBB")


# ----------------------------------------------------------------- sentiment
@pytest.mark.parametrize("headline,label", [
    ("Shares surge after record profit", "positive"),
    ("Stock plunges on weak results and downgrade", "negative"),
    ("Company holds annual general meeting", "neutral"),
    ("Firm not profitable this quarter", "negative"),      # negation flips the word
    ("Stock is not falling anymore", "positive"),
])
def test_headline_sentiment(headline, label):
    assert analysis.headline_sentiment(headline)["label"] == label


def test_news_summary_counts(monkeypatch):
    monkeypatch.setattr(market, "get_news", lambda symbols, limit=10: [
        {"title": "Profit jumps", "source": "x", "published_at": "", "link": ""},
        {"title": "Shares crash", "source": "x", "published_at": "", "link": ""},
        {"title": "Board meets", "source": "x", "published_at": "", "link": ""}])
    s = analysis.news_with_sentiment("X")["summary"]
    assert (s["positive"], s["negative"], s["neutral"]) == (1, 1, 1)


# ------------------------------------------------------------ mutual funds
NAV_NEW = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date

Open Ended Schemes(Equity Scheme - Flexi Cap Fund)

Some Mutual Fund

100001;INF000A01;-;Alpha Flexi Cap Fund;Direct Plan;Growth Option;45.5;03-Nov-2026
100002;-;-;Alpha Flexi Cap Fund;Regular Plan;IDCW Option;N.A.;03-Nov-2026
"""
NAV_OLD = """Scheme Code;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Scheme Name;Net Asset Value;Date
Open Ended Schemes(Debt Scheme - Liquid Fund)
Old House Mutual Fund
200001;INF1;-;Old Liquid Fund - Direct Plan - Growth;12.34;03-Nov-2026
"""


def test_amfi_file_parsing_handles_both_layouts():
    new = mf._parse_navall(NAV_NEW)
    assert [f["code"] for f in new] == [100001]                # the "N.A." NAV row is skipped
    assert new[0]["name"] == "Alpha Flexi Cap Fund - Direct Plan - Growth Option"
    assert new[0]["category"] == "Equity Scheme - Flexi Cap Fund" and new[0]["fund_house"] == "Some Mutual Fund"
    old = mf._parse_navall(NAV_OLD)
    assert old[0]["name"] == "Old Liquid Fund - Direct Plan - Growth" and old[0]["nav"] == 12.34


def test_xirr_of_a_simple_ten_percent_year():
    flows = [(date(2024, 1, 1), -1000.0), (date(2025, 1, 1), 1100.0)]
    assert mf._xirr(flows) == pytest.approx(10, abs=0.2)


def _nav_series():
    rows, nav, d = [], 10.0, date(2020, 1, 1)
    while d < date(2026, 1, 1):
        nav *= 1.0004
        rows.append({"date": d, "nav": round(nav, 4)})
        d += timedelta(days=1)
    return rows


def test_sip_returns_add_up(monkeypatch):
    monkeypatch.setattr(mf, "fund_history", lambda code: {"meta": {"scheme_name": "Test Fund"}, "rows": _nav_series()})
    r = mf.sip_returns(1, 5000, date(2021, 1, 5), date(2023, 1, 5))
    assert r["installments"] == 25 and r["invested"] == 125_000
    assert r["value"] > r["invested"] and r["xirr"] > 0
    assert r["gain"] == pytest.approx(r["value"] - r["invested"])


def test_sip_before_the_fund_existed_is_refused(monkeypatch):
    monkeypatch.setattr(mf, "fund_history", lambda code: {"meta": {}, "rows": _nav_series()})
    with pytest.raises(ValueError, match="starts on"):
        mf.sip_returns(1, 5000, date(2010, 1, 1))


# ------------------------------------------------------------------ tracker
def test_tracker_converts_foreign_holdings_and_survives_a_bad_symbol(monkeypatch):
    quotes = {"TCS.NS": {"name": "TCS", "yahooSymbol": "TCS.NS", "currency": "INR", "price": 4000.0, "change": 40.0, "changePercent": "1.00"},
              "AAPL": {"name": "Apple", "yahooSymbol": "AAPL", "currency": "USD", "price": 200.0, "change": -2.0, "changePercent": "-1.00"}}

    def get_quote(symbol):
        if symbol not in quotes:
            raise ValueError("No market data found")
        return quotes[symbol]
    monkeypatch.setattr(market, "get_quote", get_quote)
    monkeypatch.setattr(market, "get_fx_rate", lambda base, quote: {"rate": 90.0 if base == "USD" else 1.0})

    r = tracker.value_holdings([{"symbol": "TCS.NS", "qty": 10, "avg_price": 3000},
                                {"symbol": "AAPL", "qty": 5, "avg_price": 100},
                                {"symbol": "NOPE", "qty": 1, "avg_price": 1}])
    assert r["invested"] == pytest.approx(10 * 3000 + 5 * 100 * 90)
    assert r["value"] == pytest.approx(10 * 4000 + 5 * 200 * 90)
    assert r["pnl"] == pytest.approx(r["value"] - r["invested"])
    assert sum(x["weight_pct"] for x in r["rows"] if x["weight_pct"]) == pytest.approx(100)
    assert r["rows"][2]["error"]                              # one bad symbol must not break the rest


def test_stale_cache_is_flagged(monkeypatch):
    market._cache.clear()
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        if calls["n"] > 1:
            raise RuntimeError("yahoo down")
        return {"price": 1}
    assert market._cached("k", 0, fetch) == {"price": 1}      # ttl 0: next call tries again
    again = market._cached("k", 0, fetch)
    assert again["price"] == 1 and again["stale"] is True
