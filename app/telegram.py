"""
Price alerts on Telegram.

One FinSuite bot (TELEGRAM_BOT_TOKEN, created with @BotFather) serves every
user. A user presses "Link Telegram" in their account, which gives a link like
https://t.me/<bot>?start=<code>. Opening it and pressing Start sends the code
to the bot; the background worker reads the bot's messages every 30 seconds
and connects that chat to the account. Alerts are then sent to the chat.
"""
from __future__ import annotations

import logging
import os
import re
import secrets
import string

import requests

from . import store

log = logging.getLogger("finsuite.telegram")
LINK_MINUTES = 10
_bot_name: str | None = None


def token() -> str:
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def enabled() -> bool:
    return bool(token())


def _call(method: str, **params):
    r = requests.post(f"https://api.telegram.org/bot{token()}/{method}", json=params, timeout=15)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram error {r.status_code}"))
    return data["result"]


def bot_username() -> str:
    global _bot_name
    if not _bot_name:
        _bot_name = _call("getMe")["username"]
    return _bot_name


def send(chat_id: str, text: str) -> None:
    _call("sendMessage", chat_id=chat_id, text=text, disable_web_page_preview=True)


def new_link_code(user_id: int) -> dict:
    code = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    store.create_token(user_id, "telegram", LINK_MINUTES * 60, raw=code)
    bot = bot_username()
    return {"code": code, "bot": bot, "url": f"https://t.me/{bot}?start={code}", "expires_minutes": LINK_MINUTES}


def handle_message(message: dict) -> None:
    chat = message.get("chat") or {}
    if chat.get("type") != "private" or "id" not in chat:
        return                                   # only private chats can be linked
    chat_id, text = str(chat["id"]), (message.get("text") or "").strip()
    match = re.match(r"^/start\s+([A-Za-z0-9]{6,12})$", text)
    if match:
        user_id = store.consume_token(match.group(1).upper(), "telegram")
        if user_id:
            store.set_telegram(user_id, chat_id)
            send(chat_id, "Linked. FinSuite will send your price alerts here. Send /stop to unlink.")
        else:
            send(chat_id, "That link code is invalid or has expired. Open FinSuite, go to your account and press "
                          "Link Telegram again.")
    elif text.startswith("/start"):
        send(chat_id, "Hi, I'm the FinSuite alerts bot. To receive price alerts here, open FinSuite, go to your "
                      "account and press Link Telegram.")
    elif text == "/stop":
        store.clear_telegram_chat(chat_id)
        send(chat_id, "Unlinked. You will no longer get FinSuite alerts here.")


def poll() -> int:
    """Read new messages sent to the bot. Returns how many were handled."""
    if not enabled():
        return 0
    offset = int(store.meta_get("telegram_offset", "0") or 0)
    updates = _call("getUpdates", offset=offset, timeout=0, allowed_updates=["message"])
    for update in updates:
        offset = update["update_id"] + 1
        try:
            handle_message(update.get("message") or {})
        except Exception as e:                   # one bad message must not block the others
            log.warning("telegram message failed: %s", e)
    if updates:
        store.meta_set("telegram_offset", str(offset))
    return len(updates)
