"""
Request limits that protect the server and the AI budget.

  * RateLimiter: a sliding window per key (IP address, email ...), kept in
    memory. Fast and good enough for one server process; on hosts that run
    several instances (Vercel) each instance counts on its own.
  * Daily counters (AI questions per person and in total) live in the
    database, see store.counter_add.

Everything can be tuned with environment variables, or switched off with
FINSUITE_RATE_LIMIT=0 (used by the tests).
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


ENABLED = os.environ.get("FINSUITE_RATE_LIMIT", "1") != "0"

GENERAL_PER_MIN = _int("RATE_GENERAL_PER_MIN", 240)    # any API call, per IP
ML_PER_MIN = _int("RATE_ML_PER_MIN", 5)                # price prediction trains models
LOGIN_PER_MIN = _int("RATE_LOGIN_PER_MIN", 10)         # per IP
LOGIN_PER_EMAIL = _int("RATE_LOGIN_PER_EMAIL", 8)      # per email, per 15 minutes
REGISTER_PER_HOUR = _int("RATE_REGISTER_PER_HOUR", 6)  # per IP
EMAIL_SEND_PER_HOUR = _int("RATE_EMAIL_PER_HOUR", 4)   # reset / verify mails, per IP and per address

AI_PER_MIN = _int("AI_RATE_PER_MIN", 6)                # per IP
AI_PER_IP_DAILY = _int("AI_PER_IP_DAILY", 30)          # guests
AI_PER_USER_DAILY = _int("AI_PER_USER_DAILY", 100)     # logged-in users
AI_DAILY_LIMIT = _int("AI_DAILY_LIMIT", 500)           # whole site, per day


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_clean = time.time()

    def hit(self, key: str, limit: int, window: float) -> tuple[bool, int]:
        """Record one request. Returns (allowed, seconds until a slot frees up)."""
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return False, int(q[0] + window - now) + 1
            q.append(now)
            if now - self._last_clean > 300:           # forget idle keys
                self._last_clean = now
                for k in [k for k, v in self._hits.items() if not v or v[-1] < now - 3600]:
                    del self._hits[k]
        return True, 0


LIMITER = RateLimiter()


def client_ip(request: Request) -> str:
    """The caller's address. Behind nginx, uvicorn has already replaced the client
    address with the real one; on Vercel the platform sets these headers itself."""
    if os.environ.get("VERCEL"):
        forwarded = request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(name: str, key: str, limit: int, window: float) -> tuple[bool, int]:
    if not ENABLED:
        return True, 0
    return LIMITER.hit(f"{name}:{key}", limit, window)


def enforce(name: str, key: str, limit: int, window: float, message: str | None = None) -> None:
    ok, retry = check(name, key, limit, window)
    if not ok:
        raise HTTPException(status_code=429, headers={"Retry-After": str(retry)},
                            detail=message or f"Too many requests. Please wait {retry} seconds and try again.")


def enforce_ip(request: Request, name: str, limit: int, window: float, message: str | None = None) -> None:
    enforce(name, client_ip(request), limit, window, message)
