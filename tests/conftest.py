"""Shared test setup: isolated SQLite DB, mock AI, known secrets, no network."""
import hashlib
import hmac
import json
import os
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_tmpdir = tempfile.mkdtemp(prefix="oqila-test-")
os.environ["OQILA_DB_PATH"] = str(Path(_tmpdir) / "test.db")
os.environ["OQILA_MEDIA_DIR"] = str(Path(_tmpdir) / "media")
os.environ["OQILA_POLLER_LOCK"] = str(Path(_tmpdir) / "poller.lock")
os.environ["AI_MODE"] = "mock"
os.environ["GEMINI_API_KEY"] = ""
os.environ["ADMIN_SECRET_KEY"] = "test-admin-key-0123456789"
os.environ["SESSION_SECRET"] = "test-session-secret"
os.environ["TELEGRAM_BOT_TOKEN"] = "123456:TEST-BOT-TOKEN"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = ""
os.environ["WEBAPP_URL"] = ""
os.environ["ADMIN_TELEGRAM_IDS"] = ""

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_KEY = os.environ["ADMIN_SECRET_KEY"]


def make_init_data(tg_id: int, first_name: str = "Test", auth_date: int | None = None, token: str = BOT_TOKEN) -> str:
    """Build Telegram WebApp initData signed exactly like Telegram does."""
    fields = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAE-test",
        "user": json.dumps({"id": tg_id, "first_name": first_name, "language_code": "ru"}, separators=(",", ":")),
    }
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(fields)


@pytest.fixture(scope="session")
def app():
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture()
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_telegram_network(monkeypatch):
    """Never call the real Telegram API; record outgoing messages instead."""
    from services.telegram_service import telegram_service

    sent = []

    async def fake_send_message(chat_id, text, reply_markup=None, *args, **kwargs):
        sent.append({"chat_id": chat_id, "text": text})
        return True

    monkeypatch.setattr(telegram_service, "send_message", fake_send_message)
    return sent


def login(client, tg_id: int | None = None, token: str | None = None) -> dict:
    """Sign in as a Telegram user (tg_id) or as a browser guest; returns the login response."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    body = {"init_data": make_init_data(tg_id) if tg_id else None, "profile": {"name": "Tester"}}
    res = client.post("/api/auth/login", json=body, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def auth(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['session_token']}"}
