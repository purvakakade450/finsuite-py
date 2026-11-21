"""Accounts, saved data, alerts, limits, password reset and the health check."""
import time

import pytest

from app import alerts, limits, market, store


# ------------------------------------------------------------------- accounts
def test_register_login_and_me(client, user):
    r = client.post("/auth/login", json={"email": user["email"], "password": "password123"})
    assert r.status_code == 200
    me = client.get("/auth/me", headers=user["headers"]).json()
    assert me["user"]["email"] == user["email"] and me["user"]["email_verified"] is False


def test_bad_logins_and_duplicates_are_refused(client, user):
    assert client.post("/auth/login", json={"email": user["email"], "password": "wrong-password"}).status_code == 400
    assert client.post("/auth/register", json={"email": user["email"], "password": "password123"}).status_code == 400
    assert client.post("/auth/register", json={"email": "not-an-email", "password": "password123"}).status_code == 400
    assert client.post("/auth/register", json={"email": "a@b.co", "password": "short"}).status_code == 400
    assert client.get("/auth/me").status_code == 401


def test_logout_ends_the_session(client, user):
    client.post("/auth/logout", headers=user["headers"])
    assert client.get("/auth/me", headers=user["headers"]).status_code == 401


def test_passwords_are_not_stored_in_clear(client, user):
    with store.db() as conn:
        row = conn.execute("SELECT pw_hash, salt FROM users WHERE id=?", (user["id"],)).fetchone()
    assert "password123" not in row["pw_hash"] and len(row["salt"]) == 32


# --------------------------------------------------------------- saved data
def test_saved_data_round_trip_and_key_whitelist(client, user):
    assert client.put("/user/data/watchlist", headers=user["headers"], json={"value": ["TCS.NS"]}).status_code == 200
    assert client.get("/user/data", headers=user["headers"]).json()["watchlist"]["value"] == ["TCS.NS"]
    assert client.put("/user/data/secrets", headers=user["headers"], json={"value": 1}).status_code == 422
    assert client.put("/user/data/chat", headers=user["headers"], json={"value": [{"role": "user", "content": "hi"}]}).status_code == 200


def test_users_cannot_see_each_others_data(client, user):
    client.put("/user/data/portfolio", headers=user["headers"], json={"value": [{"symbol": "X"}]})
    other = client.post("/auth/register", json={"email": "other@example.com", "password": "password123"}).json()
    seen = client.get("/user/data", headers={"Authorization": "Bearer " + other["token"]}).json()
    assert "portfolio" not in seen


# ------------------------------------------------------------------- alerts
def test_alert_fires_once_and_can_be_rearmed(client, user, monkeypatch):
    monkeypatch.setattr(market, "get_quote", lambda s: {"price": 100.0, "currency": "INR", "name": "Test Co"})
    a = client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 50}).json()
    first = client.post("/alerts/check", headers=user["headers"]).json()
    assert first["fired"] == [a["id"]]
    assert client.post("/alerts/check", headers=user["headers"]).json()["fired"] == []
    client.post(f"/alerts/{a['id']}/rearm", headers=user["headers"])
    assert client.post("/alerts/check", headers=user["headers"]).json()["fired"] == [a["id"]]


def test_alert_below_and_not_triggered(client, user, monkeypatch):
    monkeypatch.setattr(market, "get_quote", lambda s: {"price": 100.0, "currency": "INR", "name": "Test Co"})
    client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "below", "price": 50})
    assert client.post("/alerts/check", headers=user["headers"]).json()["fired"] == []


def test_alert_email_is_sent_when_configured(client, user, monkeypatch):
    sent = []
    monkeypatch.setattr(market, "get_quote", lambda s: {"price": 100.0, "currency": "INR", "name": "Test Co"})
    monkeypatch.setattr(alerts, "email_configured", lambda: True)
    monkeypatch.setattr(alerts, "send_email", lambda to, subject, body: sent.append((to, subject)))
    client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 50})
    client.post("/alerts/check", headers=user["headers"])
    assert sent and sent[0][0] == user["email"] and "T" in sent[0][1]


def test_alert_limit_and_ownership(client, user):
    for _ in range(store.MAX_ALERTS):
        assert client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 1}).status_code == 200
    assert client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 1}).status_code == 422
    other = client.post("/auth/register", json={"email": "thief@example.com", "password": "password123"}).json()
    first = client.get("/alerts", headers=user["headers"]).json()["alerts"][0]["id"]
    client.delete(f"/alerts/{first}", headers={"Authorization": "Bearer " + other["token"]})
    assert len(client.get("/alerts", headers=user["headers"]).json()["alerts"]) == store.MAX_ALERTS


def test_run_check_needs_the_cron_secret(client, monkeypatch):
    assert client.post("/alerts/run-check").status_code == 403
    monkeypatch.setenv("CRON_SECRET", "s3cret")
    assert client.post("/alerts/run-check", headers={"Authorization": "Bearer wrong"}).status_code == 403
    assert client.post("/alerts/run-check", headers={"Authorization": "Bearer s3cret"}).status_code == 200


# ------------------------------------------------------ password reset / tokens
def test_tokens_work_once_and_expire():
    t = store.create_token(1, "reset", 60)
    assert store.consume_token(t, "verify") is None              # wrong purpose
    assert store.consume_token(t, "reset") == 1
    assert store.consume_token(t, "reset") is None               # already used
    old = store.create_token(2, "reset", -1)
    assert store.consume_token(old, "reset") is None             # expired


def test_reset_password_flow(client, user, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "email_configured", lambda: True)
    monkeypatch.setattr(alerts, "send_email", lambda to, subject, body: sent.append(body))
    assert client.post("/auth/forgot", json={"email": "nobody@example.com"}).status_code == 200   # no account: same answer
    assert client.post("/auth/forgot", json={"email": user["email"]}).status_code == 200
    token = sent[-1].split("#reset=")[1].split()[0]
    assert client.post("/auth/reset", json={"token": "x" * 30, "password": "newpassword1"}).status_code == 400
    r = client.post("/auth/reset", json={"token": token, "password": "newpassword1"})
    assert r.status_code == 200 and r.json()["user"]["email_verified"] is True
    assert client.get("/auth/me", headers=user["headers"]).status_code == 401           # old sessions are gone
    assert client.post("/auth/login", json={"email": user["email"], "password": "password123"}).status_code == 400
    assert client.post("/auth/login", json={"email": user["email"], "password": "newpassword1"}).status_code == 200
    assert client.post("/auth/reset", json={"token": token, "password": "another-one-1"}).status_code == 400   # one use only


def test_forgot_password_says_so_when_email_is_off(client):
    assert client.post("/auth/forgot", json={"email": "a@b.co"}).status_code == 503


def test_email_verification_link(client, user, monkeypatch):
    sent = []
    monkeypatch.setattr(alerts, "email_configured", lambda: True)
    monkeypatch.setattr(alerts, "send_email", lambda to, subject, body: sent.append(body))
    assert client.post("/auth/verify/send", headers=user["headers"]).status_code == 200
    token = sent[-1].split("token=")[1].split()[0]
    r = client.get(f"/auth/verify?token={token}", follow_redirects=False)
    assert r.headers["location"] == "/#verified"
    assert client.get("/auth/me", headers=user["headers"]).json()["user"]["email_verified"] is True
    assert client.get(f"/auth/verify?token={token}", follow_redirects=False).headers["location"] == "/#verify-failed"


def test_delete_account_removes_everything(client, user):
    client.put("/user/data/watchlist", headers=user["headers"], json={"value": ["X"]})
    client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 1})
    assert client.delete("/auth/me", headers=user["headers"]).status_code == 200
    assert client.get("/auth/me", headers=user["headers"]).status_code == 401
    with store.db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM alerts WHERE user_id=?", (user["id"],)).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM user_data WHERE user_id=?", (user["id"],)).fetchone()[0] == 0


# --------------------------------------------------------------------- limits
def test_sliding_window_limiter():
    rl = limits.RateLimiter()
    assert rl.hit("k", 2, 60) == (True, 0) and rl.hit("k", 2, 60) == (True, 0)
    ok, retry = rl.hit("k", 2, 60)
    assert not ok and 1 <= retry <= 61
    assert rl.hit("other", 2, 60)[0]                              # keys are independent


def test_window_expires():
    rl = limits.RateLimiter()
    rl.hit("k", 1, 0.2)
    assert not rl.hit("k", 1, 0.2)[0]
    time.sleep(0.3)
    assert rl.hit("k", 1, 0.2)[0]


def test_daily_counter_stops_at_the_cap():
    assert store.counter_add("ai:t:1", 2, "2026-11-01") == (True, 1)
    assert store.counter_add("ai:t:1", 2, "2026-11-01") == (True, 2)
    assert store.counter_add("ai:t:1", 2, "2026-11-01") == (False, 2)


def test_login_is_throttled_when_limits_are_on(client, user, monkeypatch):
    monkeypatch.setattr(limits, "ENABLED", True)
    monkeypatch.setattr(limits, "LOGIN_PER_EMAIL", 3)
    codes = [client.post("/auth/login", json={"email": user["email"], "password": "bad-password"}).status_code
             for _ in range(5)]
    assert codes[:3] == [400, 400, 400] and codes[3] == 429
    assert client.post("/auth/login", json={"email": "someone-else@example.com", "password": "x" * 9}).status_code == 400


def test_general_limit_returns_429_with_retry_after(client, monkeypatch):
    monkeypatch.setattr(limits, "ENABLED", True)
    monkeypatch.setattr(limits, "GENERAL_PER_MIN", 3)
    limits.LIMITER._hits.clear()
    codes = [client.get("/market/currencies").status_code for _ in range(5)]
    assert 429 in codes
    r = client.get("/market/currencies")
    assert r.status_code == 429 and "Retry-After" in r.headers


# --------------------------------------------------------------------- health
def test_health_endpoint(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["database"]["ok"] and r["uptime_seconds"] >= 0
