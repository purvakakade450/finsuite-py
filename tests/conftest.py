"""Shared test set-up. Tests never touch the internet or the real database:
every test run gets a fresh temporary SQLite file, the background alert
worker and the AI key are off, and rate limits are off unless a test turns
them on."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["FINSUITE_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["FINSUITE_ALERT_WORKER"] = "0"
os.environ["FINSUITE_RATE_LIMIT"] = "0"
for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "SMTP_HOST", "SMTP_FROM", "SMTP_USER", "SMTP_PASSWORD",
             "TELEGRAM_BOT_TOKEN", "CRON_SECRET", "PUBLIC_URL"):
    os.environ.pop(name, None)
os.environ["FINSUITE_NO_ENV_FILE"] = "1"      # do not read the developer's private .env

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def user(client):
    """A freshly registered user and its Authorization header."""
    import uuid
    email = f"{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": "password123", "name": "Test User"})
    assert r.status_code == 200, r.text
    data = r.json()
    return {"email": email, "id": data["user"]["id"], "headers": {"Authorization": "Bearer " + data["token"]}}
