"""
Browser push notifications (Web Push) for price alerts.

The server keeps one VAPID key pair in the database (made on first use). A
logged-in user's browser subscribes through the service worker; fired alerts
are then pushed to every subscribed device, even when FinSuite is closed.
Needs the `pywebpush` package; without it push is simply reported as off.
"""
from __future__ import annotations

import base64
import json
import logging
import os

from . import store

log = logging.getLogger("finsuite.push")


def available() -> bool:
    try:
        import pywebpush  # noqa: F401
        return True
    except ImportError:
        return False


def _private_pem() -> str:
    pem = store.meta_get("vapid_private_pem")
    if not pem:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        store.meta_set("vapid_private_pem", pem)
    return pem


def public_key() -> str:
    """The key the browser needs to subscribe (URL-safe base64 of the uncompressed point)."""
    from cryptography.hazmat.primitives import serialization
    key = serialization.load_pem_private_key(_private_pem().encode(), password=None)
    raw = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def send(sub: dict, payload: dict) -> bool:
    """Push one message to one subscription. Dead subscriptions (404/410) are removed."""
    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush
    try:
        webpush(subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                data=json.dumps(payload), vapid_private_key=Vapid.from_pem(_private_pem().encode()),
                vapid_claims={"sub": os.environ.get("VAPID_SUBJECT", "mailto:admin@finsuite.co.in")}, ttl=3600)
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            store.remove_push_sub(sub["endpoint"])
        else:
            log.warning("push failed (%s): %s", status, e)
        return False


def notify_user(user_id: int, title: str, body: str, url: str = "/#watchlist") -> int:
    """Push to every device of the user. Returns how many accepted it."""
    if not available():
        return 0
    return sum(send(sub, {"title": title, "body": body, "url": url}) for sub in store.push_subs(user_id))
