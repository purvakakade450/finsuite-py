"""
User accounts and saved data (watchlist, portfolio, price alerts) in a small
SQLite database. Standard library only.

The database file is FINSUITE_DB if set, otherwise data/finsuite.db in the
project folder (/tmp/finsuite.db on Vercel, whose project folder is read-only
and whose /tmp is wiped between deployments).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

if os.environ.get("FINSUITE_DB"):
    DB_PATH = Path(os.environ["FINSUITE_DB"])
elif os.environ.get("VERCEL"):
    DB_PATH = Path("/tmp/finsuite.db")
else:
    DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finsuite.db"
# False when the file sits somewhere that is wiped (Vercel's /tmp): accounts may reset.
PERSISTENT = bool(os.environ.get("FINSUITE_DB")) or not os.environ.get("VERCEL")

SESSION_DAYS = 30
DATA_KEYS = {"watchlist", "portfolio", "settings", "chat"}
MAX_DATA_BYTES = 100_000
MAX_ALERTS = 50
_PBKDF2_ROUNDS = 200_000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
    pw_hash TEXT NOT NULL, salt TEXT NOT NULL, email_alerts INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS user_data (
    user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, key));
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, type TEXT NOT NULL,
    price REAL NOT NULL, created_at TEXT NOT NULL, triggered_at TEXT, triggered_price REAL,
    emailed INTEGER NOT NULL DEFAULT 0, seen INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, n INTEGER NOT NULL, day TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, purpose TEXT NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS push_subs (
    endpoint TEXT PRIMARY KEY, user_id INTEGER NOT NULL, p256dh TEXT NOT NULL, auth TEXT NOT NULL, created_at TEXT NOT NULL);
"""
# Columns added after the first release; older databases get them on start-up.
_NEW_USER_COLUMNS = (("email_verified", "INTEGER NOT NULL DEFAULT 0"), ("telegram_chat_id", "TEXT"))
_ready = False


class AuthError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    global _ready
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        if not _ready:
            conn.executescript(_SCHEMA)
            have = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
            for name, ddl in _NEW_USER_COLUMNS:
                if name not in have:
                    conn.execute(f"ALTER TABLE users ADD COLUMN {name} {ddl}")
            _ready = True
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Accounts and sessions
# ---------------------------------------------------------------------------
def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _public(row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"],
            "email_alerts": bool(row["email_alerts"]), "created_at": row["created_at"],
            "email_verified": bool(row["email_verified"]), "telegram_linked": bool(row["telegram_chat_id"])}


def _new_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    conn.execute("INSERT INTO sessions VALUES (?,?,?)",
                 (_token_hash(token), user_id, time.time() + SESSION_DAYS * 86400))
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
    return token


def register(email: str, password: str, name: str) -> dict:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise AuthError("Enter a valid email address.")
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    salt = secrets.token_hex(16)
    with db() as conn:
        if conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            raise AuthError("An account with this email already exists. Log in instead.")
        cur = conn.execute("INSERT INTO users (email,name,pw_hash,salt,created_at) VALUES (?,?,?,?,?)",
                           (email, name.strip() or email.split("@")[0], _hash(password, salt), salt, _now()))
        user = conn.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
        return {"token": _new_session(conn, user["id"]), "user": _public(user)}


def login(email: str, password: str) -> dict:
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        if not user or not hmac.compare_digest(user["pw_hash"], _hash(password, user["salt"])):
            raise AuthError("Wrong email or password.")
        return {"token": _new_session(conn, user["id"]), "user": _public(user)}


def logout(token: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))


def user_for_token(token: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
                           "WHERE s.token_hash=? AND s.expires_at>?", (_token_hash(token), time.time())).fetchone()
        return _public(row) if row else None


def update_settings(user_id: int, name: str | None = None, email_alerts: bool | None = None) -> dict:
    with db() as conn:
        if name is not None and name.strip():
            conn.execute("UPDATE users SET name=? WHERE id=?", (name.strip(), user_id))
        if email_alerts is not None:
            conn.execute("UPDATE users SET email_alerts=? WHERE id=?", (int(email_alerts), user_id))
        return _public(conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


# ---------------------------------------------------------------------------
# Saved data: one JSON value per key
# ---------------------------------------------------------------------------
def get_data(user_id: int) -> dict:
    with db() as conn:
        rows = conn.execute("SELECT key, value, updated_at FROM user_data WHERE user_id=?", (user_id,)).fetchall()
    return {r["key"]: {"value": json.loads(r["value"]), "updated_at": r["updated_at"]} for r in rows}


def put_data(user_id: int, key: str, value) -> dict:
    if key not in DATA_KEYS:
        raise ValueError(f"key must be one of {sorted(DATA_KEYS)}")
    text = json.dumps(value)
    if len(text) > MAX_DATA_BYTES:
        raise ValueError("saved data is too large")
    with db() as conn:
        conn.execute("INSERT INTO user_data VALUES (?,?,?,?) ON CONFLICT(user_id,key) "
                     "DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                     (user_id, key, text, _now()))
    return {"key": key, "value": value}


# ---------------------------------------------------------------------------
# Price alerts (checked in the background by alerts.py)
# ---------------------------------------------------------------------------
def _alert(row) -> dict:
    return {k: row[k] for k in ("id", "symbol", "type", "price", "created_at", "triggered_at",
                                "triggered_price", "emailed", "seen")}


def list_alerts(user_id: int) -> list[dict]:
    with db() as conn:
        return [_alert(r) for r in conn.execute("SELECT * FROM alerts WHERE user_id=? ORDER BY id", (user_id,))]


def add_alert(user_id: int, symbol: str, type_: str, price: float) -> dict:
    if type_ not in ("above", "below"):
        raise ValueError("type must be above or below")
    with db() as conn:
        if conn.execute("SELECT COUNT(*) FROM alerts WHERE user_id=?", (user_id,)).fetchone()[0] >= MAX_ALERTS:
            raise ValueError(f"You can have at most {MAX_ALERTS} alerts.")
        cur = conn.execute("INSERT INTO alerts (user_id,symbol,type,price,created_at) VALUES (?,?,?,?,?)",
                           (user_id, symbol.strip(), type_, price, _now()))
        return _alert(conn.execute("SELECT * FROM alerts WHERE id=?", (cur.lastrowid,)).fetchone())


def delete_alert(user_id: int, alert_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM alerts WHERE id=? AND user_id=?", (alert_id, user_id))


def rearm_alert(user_id: int, alert_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE alerts SET triggered_at=NULL, triggered_price=NULL, emailed=0, seen=0 "
                     "WHERE id=? AND user_id=?", (alert_id, user_id))


def mark_alerts_seen(user_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE alerts SET seen=1 WHERE user_id=? AND triggered_at IS NOT NULL", (user_id,))


def pending_alerts(user_id: int | None = None) -> list[dict]:
    """Alerts not yet triggered, with their owner's email settings."""
    sql = ("SELECT a.*, u.email, u.name, u.email_alerts, u.telegram_chat_id FROM alerts a JOIN users u ON u.id=a.user_id "
           "WHERE a.triggered_at IS NULL" + (" AND a.user_id=?" if user_id else ""))
    with db() as conn:
        return [dict(r) for r in conn.execute(sql, (user_id,) if user_id else ())]


def set_triggered(alert_id: int, price: float) -> bool:
    """Mark an alert as fired. False if another worker got there first."""
    with db() as conn:
        cur = conn.execute("UPDATE alerts SET triggered_at=?, triggered_price=? WHERE id=? AND triggered_at IS NULL",
                           (_now(), price, alert_id))
        return cur.rowcount == 1


def set_emailed(alert_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE alerts SET emailed=1 WHERE id=?", (alert_id,))


def claim_run(name: str, every_seconds: float) -> bool:
    """True for exactly one caller per interval, across processes (uvicorn workers)."""
    now = time.time()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT value FROM meta WHERE key=?", (name,)).fetchone()
        if row and now - float(row["value"]) < every_seconds:
            return False
        conn.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                     (name, str(now)))
        return True


# ---------------------------------------------------------------------------
# Daily counters (AI usage caps)
# ---------------------------------------------------------------------------
def counter_add(key: str, limit: int, day: str) -> tuple[bool, int]:
    """Add one to a per-day counter unless it already reached `limit`."""
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT n FROM counters WHERE key=?", (key,)).fetchone()
        n = row["n"] if row else 0
        if n >= limit:
            return False, n
        conn.execute("INSERT INTO counters VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET n=excluded.n",
                     (key, n + 1, day))
        conn.execute("DELETE FROM counters WHERE day < ?", (_days_ago(day, 3),))
        return True, n + 1


def _days_ago(day: str, n: int) -> str:
    from datetime import date, timedelta
    return (date.fromisoformat(day) - timedelta(days=n)).isoformat()


def meta_get(key: str, default: str | None = None) -> str | None:
    with db() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def meta_set(key: str, value: str) -> None:
    with db() as conn:
        conn.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


# ---------------------------------------------------------------------------
# One-time tokens: password reset, email verification, Telegram link codes
# ---------------------------------------------------------------------------
def create_token(user_id: int, purpose: str, ttl_seconds: int, raw: str | None = None) -> str:
    raw = raw or secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute("DELETE FROM tokens WHERE expires_at < ? OR (user_id=? AND purpose=?)",
                     (time.time(), user_id, purpose))
        conn.execute("INSERT INTO tokens VALUES (?,?,?,?)",
                     (_token_hash(raw), user_id, purpose, time.time() + ttl_seconds))
    return raw


def consume_token(raw: str, purpose: str) -> int | None:
    """Use a token once. Returns the user id, or None if it is unknown, used or expired."""
    with db() as conn:
        row = conn.execute("SELECT user_id FROM tokens WHERE token_hash=? AND purpose=? AND expires_at>?",
                           (_token_hash(raw.strip()), purpose, time.time())).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM tokens WHERE token_hash=?", (_token_hash(raw.strip()),))
        return row["user_id"]


def get_user_by_email(email: str) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
        return _public(row) if row else None


def set_password(user_id: int, password: str) -> None:
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.")
    salt = secrets.token_hex(16)
    with db() as conn:
        conn.execute("UPDATE users SET pw_hash=?, salt=? WHERE id=?", (_hash(password, salt), salt, user_id))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))      # log out everywhere


def mark_verified(user_id: int) -> None:
    with db() as conn:
        conn.execute("UPDATE users SET email_verified=1 WHERE id=?", (user_id,))


def delete_user(user_id: int) -> None:
    with db() as conn:
        for table in ("sessions", "user_data", "alerts", "tokens", "push_subs"):
            conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))


# ---------------------------------------------------------------------------
# Notification channels: browser push and Telegram
# ---------------------------------------------------------------------------
def add_push_sub(user_id: int, endpoint: str, p256dh: str, auth: str) -> None:
    with db() as conn:
        conn.execute("INSERT INTO push_subs VALUES (?,?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET "
                     "user_id=excluded.user_id, p256dh=excluded.p256dh, auth=excluded.auth",
                     (endpoint, user_id, p256dh, auth, _now()))


def remove_push_sub(endpoint: str, user_id: int | None = None) -> None:
    with db() as conn:
        if user_id is None:
            conn.execute("DELETE FROM push_subs WHERE endpoint=?", (endpoint,))
        else:
            conn.execute("DELETE FROM push_subs WHERE endpoint=? AND user_id=?", (endpoint, user_id))


def push_subs(user_id: int) -> list[dict]:
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM push_subs WHERE user_id=?", (user_id,))]


def set_telegram(user_id: int, chat_id: str | None) -> None:
    with db() as conn:
        conn.execute("UPDATE users SET telegram_chat_id=? WHERE id=?", (chat_id, user_id))


def start_session(user_id: int) -> dict:
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return {"token": _new_session(conn, user["id"]), "user": _public(user)}


def clear_telegram_chat(chat_id: str) -> None:
    with db() as conn:
        conn.execute("UPDATE users SET telegram_chat_id=NULL WHERE telegram_chat_id=?", (chat_id,))
