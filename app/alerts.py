"""
Background price alerts for logged-in users.

A worker thread checks every saved alert against live prices every
ALERT_INTERVAL seconds, even when nobody has FinSuite open. A fired alert is
marked in the database (shown in the app on the next visit) and, if SMTP is
configured, emailed to the user.

Email settings (environment variables):
    SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM

On hosts without long-running processes (Vercel), call
POST /alerts/run-check from a cron job instead, with the header
"Authorization: Bearer $CRON_SECRET".
"""
from __future__ import annotations

import logging
import os
import smtplib
import threading
from email.message import EmailMessage

from . import market, store

ALERT_INTERVAL = int(os.environ.get("ALERT_INTERVAL", 300))
log = logging.getLogger("finsuite.alerts")


def email_configured() -> bool:
    if os.environ.get("SMTP_USER") and not os.environ.get("SMTP_PASSWORD"):
        return False
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def explain_smtp_error(e: Exception) -> str:
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return ("The mail server rejected the login. For Gmail, SMTP_PASSWORD must be a 16-letter "
                "App Password (myaccount.google.com/apppasswords), not your normal password.")
    return f"Could not send the email: {e}"


def send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.environ["SMTP_FROM"], to, subject
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587)), timeout=20) as s:
        s.starttls()
        if os.environ.get("SMTP_USER"):
            # Google shows App Passwords in groups of four; the spaces are not part of it.
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", "").replace(" ", ""))
        s.send_message(msg)


def _hit(alert: dict, price: float) -> bool:
    return price > alert["price"] if alert["type"] == "above" else price < alert["price"]


def check_alerts(user_id: int | None = None) -> dict:
    """Check pending alerts (all users, or one) against live prices."""
    pending = store.pending_alerts(user_id)
    prices, fired, errors = {}, [], []
    for sym in {a["symbol"] for a in pending}:
        try:
            q = market.get_quote(sym)
            prices[sym] = (q["price"], q.get("currency"), q.get("name"))
        except Exception as e:
            errors.append(f"{sym}: {e}")
    for a in pending:
        if a["symbol"] not in prices:
            continue
        price, currency, name = prices[a["symbol"]]
        if price is None or not _hit(a, price) or not store.set_triggered(a["id"], price):
            continue
        fired.append(a["id"])
        if a["email_alerts"] and email_configured():
            word = "risen above" if a["type"] == "above" else "fallen below"
            try:
                send_email(a["email"], f"FinSuite alert: {a['symbol']} has {word} {a['price']:,.2f}",
                           f"Hi {a['name']},\n\n{name or a['symbol']} ({a['symbol']}) has {word} your target "
                           f"of {a['price']:,.2f} {currency or ''}. Latest price: {price:,.2f} {currency or ''}.\n\n"
                           "The alert is now switched off. Re-arm it in FinSuite > Watchlist & Alerts.\n\n"
                           "FinSuite (educational tool, not investment advice)")
                store.set_emailed(a["id"])
            except Exception as e:
                log.warning("alert email to %s failed: %s", a["email"], e)
                errors.append(f"email: {e}")
    return {"checked": len(pending), "fired": fired, "errors": errors}


def _loop(stop: threading.Event) -> None:
    while not stop.wait(30):
        try:
            if store.claim_run("alerts_last_run", ALERT_INTERVAL - 5):
                result = check_alerts()
                if result["fired"]:
                    log.info("price alerts fired: %s", result["fired"])
        except Exception as e:      # keep the worker alive through data-source hiccups
            log.warning("alert check failed: %s", e)


def start_worker() -> threading.Event | None:
    if os.environ.get("VERCEL") or os.environ.get("FINSUITE_ALERT_WORKER", "1") == "0":
        return None
    stop = threading.Event()
    threading.Thread(target=_loop, args=(stop,), name="finsuite-alerts", daemon=True).start()
    return stop
