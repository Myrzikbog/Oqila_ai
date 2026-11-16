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
os.environ["GUESTS_PER_IP_PER_HOUR"] = "0"  # every test logs in from the same address; the limit has its own test
os.environ["UZUM_KEY_FILE"] = str(Path(_tmpdir) / "uzum.key")

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


def media_qs(client, data: dict) -> str:
    """`mt=<media token>` for URLs opened by <img>/<a> tags (the session token is not accepted in URLs)."""
    res = client.post("/api/media-token", headers=auth(data))
    assert res.status_code == 200, res.text
    return "mt=" + res.json()["media_token"]


@pytest.fixture()
def fake_ai(monkeypatch):
    """A working AI without the network: the text call answers with a fixed card (no picture).

    Tests run with AI_MODE=mock, where every generation is an `ai_fallback` that is not saved; tests that
    need real cards in the history use this fixture."""
    from services import ai_service as ai_module

    calls = []

    async def fake_multimodal(self, image_bytes=None, image_mime="image/jpeg", cost_price=None, desired_price=None,
                              note=None, lang="ru", photoshoot_style="minimal_studio", **kwargs):
        calls.append({"style": photoshoot_style, "note": note, "has_image": bool(image_bytes)})
        result = self._mock_response(lang, cost_price, desired_price, note)
        result["photoshoot_style"] = photoshoot_style
        return result

    import types

    # Patched on the instance: monkeypatch restores instance attributes by assignment, so a test that patched
    # the instance earlier leaves a bound original there, which would shadow a patch of the class.
    monkeypatch.setattr(ai_module.ai_service, "_call_gemini_multimodal", types.MethodType(fake_multimodal, ai_module.ai_service))
    monkeypatch.setattr(ai_module.ai_service, "_client", object())
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    return calls


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real Gemini API; run by hand with OQILA_LIVE=1 and GEMINI_API_KEY")


class FakeLegalModel:
    """A scripted Gemini for the legal assistant: tells the three kinds of request apart (draft with tools,
    search with grounding, JSON format) and records every one of them."""

    def __init__(self):
        import json as _json
        self.json = _json
        self.calls = []
        self.draft = "Налог с оборота для самозанятых и ЯТТ — 1% [F:turnover_rate]. NEEDS_SEARCH: no"
        self.search_text = "Проверено по открытым источникам: ставка 1%."
        self.grounding = []
        self.tool_script = None   # callable(tools_by_name) run during the draft call, like the SDK's function calling
        self.formats = []         # answers returned by the successive format calls (the last one repeats)
        self.raise_on = {}        # stage -> exception

    def answer(self, **kw):
        base = {"short_answer": "Ставка налога с оборота — 1%.", "steps": ["Платите до 15 числа."], "documents": [], "where_to_go": [],
                "deadlines": [], "costs": [], "risks": [], "sources": [], "follow_up_questions": ["Когда платить?", "Нужна ли касса?", "Как открыть ЯТТ?"],
                "confidence": "high", "escalate": False, "escalate_reason": ""}
        base.update(kw)
        return base

    async def __call__(self, kind, models, contents, config, accept=None):
        import types as _types
        tools = list(config.tools or [])
        stage = "search" if any(getattr(t, "google_search", None) for t in tools) else "format" if config.response_schema else "draft"
        self.calls.append({"stage": stage, "kind": kind, "models": models, "contents": contents, "config": config,
                           "system": config.system_instruction})
        if stage in self.raise_on:
            raise self.raise_on[stage]
        if stage == "draft":
            if self.tool_script:
                self.tool_script({f.__name__: f for f in tools if callable(f)})
            return _types.SimpleNamespace(text=self.draft)
        if stage == "search":
            chunks = [_types.SimpleNamespace(web=_types.SimpleNamespace(uri=u, title=t, domain=d)) for u, t, d in self.grounding]
            meta = _types.SimpleNamespace(grounding_chunks=chunks)
            return _types.SimpleNamespace(text=self.search_text, candidates=[_types.SimpleNamespace(grounding_metadata=meta)])
        n = len([c for c in self.calls if c["stage"] == "format"]) - 1
        item = self.formats[min(n, len(self.formats) - 1)] if self.formats else self.answer()
        return _types.SimpleNamespace(text=item if isinstance(item, str) else self.json.dumps(item, ensure_ascii=False))

    def stages(self):
        return [c["stage"] for c in self.calls]


@pytest.fixture()
def fake_legal(monkeypatch):
    """The legal assistant with a working (scripted) AI."""
    from services import ai_service as ai_module

    model = FakeLegalModel()
    monkeypatch.setattr(ai_module.ai_service, "_client", object())
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    monkeypatch.setattr(ai_module.ai_service, "_generate", model)
    monkeypatch.delenv("LEGAL_SEARCH", raising=False)
    return model
