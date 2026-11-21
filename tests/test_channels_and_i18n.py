"""Browser push, Telegram, and the Hindi / Marathi Knowledge Center."""
import base64
import json
from types import SimpleNamespace

import pytest

from app import ai_assistant, alerts, market, push, store, telegram, translate
from app.glossary import GLOSSARY


# ----------------------------------------------------------------------- push
def test_vapid_key_is_made_once_and_is_a_valid_point(client):
    key = client.get("/push/key").json()
    assert key["enabled"] is True
    raw = base64.urlsafe_b64decode(key["publicKey"] + "=" * (-len(key["publicKey"]) % 4))
    assert len(raw) == 65 and raw[0] == 4                       # uncompressed P-256 point
    assert client.get("/push/key").json()["publicKey"] == key["publicKey"]


SUB = {"endpoint": "https://push.example.com/abc123def", "keys": {"p256dh": "BPublicKeyValue123", "auth": "authsecret1"}}


def test_subscribe_and_unsubscribe(client, user):
    assert client.post("/push/subscribe", json=SUB).status_code == 401
    assert client.post("/push/subscribe", json=SUB, headers=user["headers"]).status_code == 200
    assert [s["endpoint"] for s in store.push_subs(user["id"])] == [SUB["endpoint"]]
    assert client.post("/push/subscribe", json={**SUB, "endpoint": "http://not-https.example/x"}, headers=user["headers"]).status_code == 422
    client.post("/push/unsubscribe", json={"endpoint": SUB["endpoint"]}, headers=user["headers"])
    assert store.push_subs(user["id"]) == []


def test_push_sends_json_payload_and_drops_dead_subscriptions(user, monkeypatch):
    import pywebpush
    calls = []

    def fake_webpush(**kw):
        calls.append(kw)
        if kw["subscription_info"]["endpoint"].endswith("dead"):
            raise pywebpush.WebPushException("gone", response=SimpleNamespace(status_code=410))
    monkeypatch.setattr(pywebpush, "webpush", fake_webpush)
    store.add_push_sub(user["id"], "https://push.example.com/alive", "BKeyAlive123456", "auth12345")
    store.add_push_sub(user["id"], "https://push.example.com/dead", "BKeyDead1234567", "auth12345")
    assert push.notify_user(user["id"], "Title", "Body") == 1
    assert json.loads(calls[0]["data"]) == {"title": "Title", "body": "Body", "url": "/#watchlist"}
    assert [s["endpoint"] for s in store.push_subs(user["id"])] == ["https://push.example.com/alive"]


def test_fired_alert_reaches_push_and_telegram(client, user, monkeypatch):
    got = {"push": [], "telegram": []}
    monkeypatch.setattr(market, "get_quote", lambda s: {"price": 100.0, "currency": "INR", "name": "Test Co"})
    monkeypatch.setattr(push, "notify_user", lambda uid, title, body, url="/#watchlist": got["push"].append((uid, title)) or 1)
    monkeypatch.setattr(telegram, "enabled", lambda: True)
    monkeypatch.setattr(telegram, "send", lambda chat, text: got["telegram"].append((chat, text)))
    store.set_telegram(user["id"], "555")
    client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 50})
    client.post("/alerts/check", headers=user["headers"])
    assert got["push"][0][0] == user["id"] and "T" in got["push"][0][1]
    assert got["telegram"][0][0] == "555" and "Re-arm" in got["telegram"][0][1]


def test_a_failing_channel_does_not_stop_the_others(client, user, monkeypatch):
    sent = []
    monkeypatch.setattr(market, "get_quote", lambda s: {"price": 100.0, "currency": "INR", "name": "Test Co"})
    monkeypatch.setattr(push, "notify_user", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("push down")))
    monkeypatch.setattr(telegram, "enabled", lambda: True)
    monkeypatch.setattr(telegram, "send", lambda chat, text: sent.append(chat))
    store.set_telegram(user["id"], "777")
    client.post("/alerts", headers=user["headers"], json={"symbol": "T", "type": "above", "price": 50})
    result = client.post("/alerts/check", headers=user["headers"]).json()
    assert result["fired"] and sent == ["777"] and any("push" in e for e in result["errors"])


# ------------------------------------------------------------------- telegram
@pytest.fixture()
def tg(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(telegram, "_bot_name", "FinSuiteBot")
    replies = []
    monkeypatch.setattr(telegram, "send", lambda chat, text: replies.append((chat, text)))
    return replies


def test_link_flow_connects_the_chat_to_the_account(client, user, tg):
    link = client.post("/auth/telegram/link", headers=user["headers"]).json()
    assert link["url"] == f"https://t.me/FinSuiteBot?start={link['code']}" and len(link["code"]) == 8
    telegram.handle_message({"chat": {"id": 4242, "type": "private"}, "text": f"/start {link['code']}"})
    assert client.get("/auth/me", headers=user["headers"]).json()["user"]["telegram_linked"] is True
    assert "Linked" in tg[-1][1]
    telegram.handle_message({"chat": {"id": 4242, "type": "private"}, "text": f"/start {link['code']}"})   # code is single use
    assert "invalid" in tg[-1][1]


def test_stop_unlinks_and_groups_are_ignored(client, user, tg):
    store.set_telegram(user["id"], "999")
    telegram.handle_message({"chat": {"id": 1, "type": "group"}, "text": "/stop"})
    assert tg == []
    telegram.handle_message({"chat": {"id": 999, "type": "private"}, "text": "/stop"})
    assert client.get("/auth/me", headers=user["headers"]).json()["user"]["telegram_linked"] is False


def test_unlink_endpoint_and_availability(client, user, monkeypatch):
    assert client.post("/auth/telegram/link", headers=user["headers"]).status_code == 503      # no bot token set
    store.set_telegram(user["id"], "5")
    client.delete("/auth/telegram", headers=user["headers"])
    assert client.get("/auth/me", headers=user["headers"]).json()["user"]["telegram_linked"] is False


def test_polling_reads_updates_once(tg, monkeypatch):
    updates = [{"update_id": 10, "message": {"chat": {"id": 1, "type": "private"}, "text": "/start"}},
               {"update_id": 11, "message": {"chat": {"id": 1, "type": "private"}, "text": "hello"}}]
    seen = []
    monkeypatch.setattr(telegram, "_call", lambda method, **p: seen.append(p.get("offset")) or (updates if p.get("offset", 0) < 12 and len(seen) == 1 else []))
    assert telegram.poll() == 2 and store.meta_get("telegram_offset") == "12"
    assert telegram.poll() == 0


# ---------------------------------------------------------------- translations
def _fake_translation(lang, entries):
    return [{"term": e["term"], "q": f"[{lang}] {e['q']}", "a": f"[{lang}] {e['a']}", "example": f"[{lang}] {e['example']}" if e["example"] else ""}
            for e in entries]


def test_glossary_stays_english_by_default_and_rejects_other_languages(client):
    assert client.get("/knowledge/glossary").json()["lang"] == "en"
    assert client.get("/knowledge/glossary?lang=fr").status_code == 422


def test_without_the_ai_key_other_languages_fall_back_to_english(client):
    d = client.get("/knowledge/glossary?lang=hi").json()
    assert d["available"] is False and d["translated"] == 0
    assert d["glossary"][0]["q"] == GLOSSARY[0]["q"] and d["glossary"][0]["translated"] is False


def test_translations_are_made_once_and_cached(client, monkeypatch):
    monkeypatch.setattr(ai_assistant, "enabled", lambda: True)
    calls = []
    monkeypatch.setattr(translate, "translate_batch", lambda lang, entries: calls.append(len(entries)) or _fake_translation(lang, entries))
    with store.db() as conn:
        conn.execute("DELETE FROM translations") if conn.execute("SELECT name FROM sqlite_master WHERE name='translations'").fetchone() else None
    first = client.get("/knowledge/glossary?lang=mr").json()
    assert first["available"] is True
    import time
    for _ in range(100):                                       # the work runs in the background
        d = client.get("/knowledge/glossary?lang=mr").json()
        if not d["pending"] and d["translated"] == d["total"]:
            break
        time.sleep(0.1)
    assert d["translated"] == d["total"] == len(GLOSSARY)
    assert d["glossary"][0]["q"].startswith("[mr] ") and d["glossary"][0]["translated"] is True
    assert sum(calls) == len(GLOSSARY) and max(calls) <= translate.BATCH
    n = len(calls)
    client.get("/knowledge/glossary?lang=mr")
    assert len(calls) == n                                     # nothing left to translate: no new AI calls


def test_ai_language_note_is_added_to_the_prompt():
    assert "Hindi" in ai_assistant.LANGUAGE_NOTES["hi"] and "Marathi" in ai_assistant.LANGUAGE_NOTES["mr"]


def test_chat_accepts_only_known_languages(client):
    body = {"messages": [{"role": "user", "content": "hi"}]}
    assert client.post("/assistant/ai-chat", json={**body, "language": "hi"}).status_code == 200
    assert client.post("/assistant/ai-chat", json={**body, "language": "xx"}).status_code == 422


def test_a_failed_batch_is_retried_and_does_not_stop_the_rest(client, monkeypatch):
    monkeypatch.setattr(ai_assistant, "enabled", lambda: True)
    with store.db() as conn:
        conn.execute("DELETE FROM translations") if conn.execute("SELECT name FROM sqlite_master WHERE name='translations'").fetchone() else None
    seen = {"calls": 0, "first": None}

    def flaky(lang, entries):
        seen["calls"] += 1
        if seen["first"] is None:
            seen["first"] = entries[0]["term"]
        if entries[0]["term"] == seen["first"] and seen["calls"] <= 3:     # the first batch fails every time
            raise RuntimeError("slow upstream")
        return _fake_translation(lang, entries)
    monkeypatch.setattr(translate, "translate_batch", flaky)
    import time
    client.get("/knowledge/glossary?lang=hi")
    for _ in range(100):
        d = client.get("/knowledge/glossary?lang=hi").json()
        if not d["pending"]:
            break
        time.sleep(0.1)
    # the failed batch did not stop the others, and the next visit picks it up again
    assert d["translated"] >= d["total"] - translate.BATCH
    for _ in range(100):
        d = client.get("/knowledge/glossary?lang=hi").json()
        if d["translated"] == d["total"]:
            break
        time.sleep(0.1)
    assert d["translated"] == d["total"]
