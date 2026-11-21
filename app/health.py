"""
Health checks: a quick one for uptime monitors (is the app and its database
alive?) and a deeper one that also tests the outside data sources, shown on
the Data Sources tab.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from . import ai_assistant, alerts, mf, store

STARTED = time.time()
DEEP_TTL = 60
_cache: dict = {"at": 0.0, "value": None}
_lock = threading.Lock()


def _timed(fn) -> dict:
    t = time.time()
    try:
        fn()
        return {"ok": True, "ms": int((time.time() - t) * 1000)}
    except Exception as e:
        return {"ok": False, "ms": int((time.time() - t) * 1000), "error": str(e)[:140]}


def _yahoo() -> None:
    import yfinance as yf
    if yf.Ticker("^NSEI").history(period="5d").empty:
        raise RuntimeError("no data returned")


def _amfi() -> None:
    last: Exception | None = None
    for url in mf.AMFI_URLS:                  # healthy if either address answers
        try:
            requests.head(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, allow_redirects=True).raise_for_status()
            return
        except Exception as e:
            last = e
    raise last


def _news() -> None:
    requests.get("https://news.google.com/rss/search?q=nifty&hl=en-IN&gl=IN&ceid=IN:en",
                 headers={"User-Agent": "Mozilla/5.0"}, timeout=8).raise_for_status()


def _database() -> None:
    with store.db() as conn:
        conn.execute("SELECT 1").fetchone()


def check_sources() -> dict:
    """Test each outside data source (cached for a minute so it can't be used to hammer them)."""
    with _lock:
        if _cache["value"] and time.time() - _cache["at"] < DEEP_TTL:
            return _cache["value"]
    jobs = {"Yahoo Finance": _yahoo, "AMFI mutual fund NAVs": _amfi, "Google News": _news}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {name: pool.submit(_timed, fn) for name, fn in jobs.items()}
        value = {name: f.result() for name, f in futures.items()}
    with _lock:
        _cache.update(at=time.time(), value=value)
    return value


def report(deep: bool = False) -> dict:
    db = _timed(_database)
    out = {
        "status": "ok" if db["ok"] else "down",
        "uptime_seconds": int(time.time() - STARTED),
        "database": db,
        "ai_assistant": ai_assistant.enabled(),
        "email_alerts": alerts.email_configured(),
        "accounts_persistent": store.PERSISTENT,
    }
    if deep:
        out["sources"] = check_sources()
        if not all(s["ok"] for s in out["sources"].values()) and out["status"] == "ok":
            out["status"] = "degraded"
    return out
