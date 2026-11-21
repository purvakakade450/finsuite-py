#!/usr/bin/env python3
"""Uptime check, run by cron every 5 minutes.

Asks the app's /api/health. After two failures in a row it emails the admin
once ("FinSuite is down"), and once more when it recovers. The admin address is
ADMIN_EMAIL (default: SMTP_USER) from /etc/finsuite.env. Standard library only.
"""
import json
import os
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from pathlib import Path

URL = os.environ.get("FINSUITE_HEALTH_URL", "http://127.0.0.1:8000/api/health")
STATE = Path(os.environ.get("FINSUITE_HEALTH_STATE", "/var/lib/finsuite/health.state"))
ENV_FILE = Path("/etc/finsuite.env")


def load_env() -> dict:
    env = dict(os.environ)
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def send(env: dict, subject: str, body: str) -> None:
    to = env.get("ADMIN_EMAIL") or env.get("SMTP_USER")
    if not (to and env.get("SMTP_HOST") and env.get("SMTP_FROM")):
        print(f"{subject}: {body} (no email configured)", file=sys.stderr)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = env["SMTP_FROM"], to, subject
    msg.set_content(body)
    with smtplib.SMTP(env["SMTP_HOST"], int(env.get("SMTP_PORT", 587)), timeout=20) as s:
        s.starttls()
        if env.get("SMTP_USER"):
            s.login(env["SMTP_USER"], env.get("SMTP_PASSWORD", "").replace(" ", ""))
        s.send_message(msg)


def check() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(URL, timeout=15) as r:
            data = json.load(r)
            return r.status == 200 and data.get("status") != "down", json.dumps(data)[:300]
    except Exception as e:
        return False, str(e)


def main() -> int:
    env = load_env()
    state = {"fails": 0, "alerted": False}
    try:
        state.update(json.loads(STATE.read_text()))
    except Exception:
        pass
    ok, detail = check()
    if ok:
        if state["alerted"]:
            send(env, "FinSuite is back up", "The health check is passing again.")
        state = {"fails": 0, "alerted": False}
    else:
        state["fails"] += 1
        if state["fails"] >= 2 and not state["alerted"]:
            send(env, "FinSuite is DOWN", f"The health check failed {state['fails']} times in a row.\n\n{detail}\n\n"
                      "On the server: sudo systemctl status finsuite ; sudo journalctl -u finsuite -n 50")
            state["alerted"] = True
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
