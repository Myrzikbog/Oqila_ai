"""AI rate limits, photo file storage, public stats and the demo seed script."""
import base64
import io
import sqlite3

import pytest
from PIL import Image

from conftest import auth, login


def _png_data_url() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "teal").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


# --- Rate limits ---------------------------------------------------------------------------

def test_generate_card_is_rate_limited_per_user(client, monkeypatch):
    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "2")
    alice = login(client, tg_id=920001)
    bob = login(client, tg_id=920002)
    for _ in range(2):
        assert client.post("/api/generate-card", data={"note": "x", "generate_photo": "false"}, headers=auth(alice)).status_code == 200
    blocked = client.post("/api/generate-card", data={"note": "x", "lang": "uz", "generate_photo": "false"}, headers=auth(alice))
    assert blocked.status_code == 429
    assert "so'rov" in blocked.json()["detail"]
    # Another user is not affected
    assert client.post("/api/generate-card", data={"note": "x", "generate_photo": "false"}, headers=auth(bob)).status_code == 200


def test_legal_qa_is_rate_limited(client, monkeypatch):
    monkeypatch.setenv("AI_LEGAL_LIMIT_PER_HOUR", "1")
    user = login(client, tg_id=920003)
    assert client.post("/api/legal-qa", json={"question": "YaTT qanday ochiladi?"}, headers=auth(user)).status_code == 200
    assert client.post("/api/legal-qa", json={"question": "Soliq qancha?"}, headers=auth(user)).status_code == 429


def test_global_budget_switches_to_mock_instead_of_failing(client, monkeypatch):
    from services import ai_service as ai_module
    from services.database import log_event

    calls = []

    async def fake_gemini(*args, **kwargs):
        calls.append(1)
        return {"title": "real", "description": "", "price_tag": "", "hashtags": [], "marketing_tip": ""}

    monkeypatch.setattr(ai_module.ai_service, "_client", object())
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    monkeypatch.setattr(ai_module.ai_service, "_call_gemini_multimodal", fake_gemini)
    user = login(client, tg_id=920004)

    monkeypatch.setenv("AI_GLOBAL_DAILY_LIMIT", "1000000")
    assert client.post("/api/generate-card", data={"note": "x"}, headers=auth(user)).json()["title"] == "real"

    monkeypatch.setenv("AI_GLOBAL_DAILY_LIMIT", "1")
    log_event("generate_card", is_mock=False, user_id=user["user_id"])
    res = client.post("/api/generate-card", data={"note": "x"}, headers=auth(user))
    assert res.status_code == 200 and res.json()["title"] != "real"
    assert len(calls) == 1


def test_demo_card_never_calls_gemini(client, monkeypatch):
    from services import ai_service as ai_module

    async def boom(*args, **kwargs):
        raise AssertionError("demo card must not call Gemini")

    monkeypatch.setattr(ai_module.ai_service, "_client", object())
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    monkeypatch.setattr(ai_module.ai_service, "_call_gemini_multimodal", boom)
    user = login(client, tg_id=920005)
    assert client.get("/api/demo-card", headers=auth(user)).status_code == 200


# --- Photos stored as files -------------------------------------------------------------------

def test_card_photo_is_stored_as_file_and_served(client):
    from services.database import DB_PATH, save_generated_card
    from services.media_storage import resolve_photo

    alice = login(client, tg_id=930001)
    bob = login(client, tg_id=930002)
    card_id = save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="", studio_photo_url=_png_data_url(), user_id=alice["user_id"])

    with sqlite3.connect(DB_PATH) as conn:
        stored = conn.execute("SELECT studio_photo_url FROM generated_cards WHERE id = ?", (card_id,)).fetchone()[0]
    assert stored.startswith("file:cards/") and resolve_photo(stored)

    item = next(i for i in client.get("/api/history", headers=auth(alice)).json()["items"] if i["id"] == card_id)
    assert item["studio_photo_url"] == f"/api/cards/{card_id}/photo"
    res = client.get(f"/api/cards/{card_id}/photo?token={alice['session_token']}")
    assert res.status_code == 200 and res.headers["content-type"] == "image/png"
    assert client.get(f"/api/cards/{card_id}/photo", headers=auth(bob)).status_code == 404

    # Deleting the card removes the file
    path = resolve_photo(stored)
    assert client.delete(f"/api/history/{card_id}", headers=auth(alice)).status_code == 200
    assert not path.exists()


def test_admin_can_view_any_card_photo(client):
    from conftest import ADMIN_KEY
    from services.database import save_generated_card

    owner = login(client, tg_id=930003)
    card_id = save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="", studio_photo_url=_png_data_url(), user_id=owner["user_id"])
    assert client.get(f"/api/admin/cards/{card_id}/photo").status_code == 403
    assert client.get(f"/api/admin/cards/{card_id}/photo", headers={"X-Admin-Key": ADMIN_KEY}).status_code == 200


def test_migration_moves_legacy_inline_photos(client):
    from scripts.migrate_photos_to_files import migrate
    from services.database import DB_PATH

    owner = login(client, tg_id=930004)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO generated_cards (title, studio_photo_url, user_id) VALUES ('legacy', ?, ?)",
            (_png_data_url(), owner["user_id"]),
        )
        card_id = cur.lastrowid
    assert migrate() >= 1
    with sqlite3.connect(DB_PATH) as conn:
        value = conn.execute("SELECT studio_photo_url FROM generated_cards WHERE id = ?", (card_id,)).fetchone()[0]
    assert value.startswith("file:")
    assert client.get(f"/api/cards/{card_id}/photo", headers=auth(owner)).status_code == 200


def test_photo_path_cannot_escape_media_dir():
    from services.media_storage import resolve_photo

    assert resolve_photo("file:../../main.py") is None
    assert resolve_photo("file:/etc/passwd") is None


# --- Public stats & demo seeding ----------------------------------------------------------------

def test_public_stats_are_aggregate_only(client):
    login(client, tg_id=940001)
    client.post("/api/legal-qa", json={"question": "secret question text"}, headers=auth(login(client, tg_id=940002)))
    res = client.get("/api/stats")
    assert res.status_code == 200
    body = res.text
    assert "secret question text" not in body and "recent_logs" not in body
    data = res.json()
    for key in ("users_total", "cards_total", "calculations_total", "daily_activity", "bot_username"):
        assert key in data
    assert len(data["daily_activity"]) == 14


def test_demo_data_is_excluded_from_public_stats(client):
    from scripts.seed_demo import seed

    before = client.get("/api/stats").json()
    user = login(client, tg_id=950001)
    client.get("/api/demo-card", headers=auth(user))  # "quick demo" sample: not real usage
    seed(950002, lang="ru")
    after = client.get("/api/stats").json()
    assert after["cards_total"] == before["cards_total"]
    assert after["users_total"] == before["users_total"] + 1  # only the real user 950001
    assert after["uzum_connected_users"] == before["uzum_connected_users"]


def test_seed_demo_fills_the_account(client):
    from conftest import make_init_data
    from scripts.seed_demo import seed

    seed(950003, lang="uz", reset=True)
    seed(950003, lang="uz", reset=True)  # idempotent with --reset
    res = client.post("/api/auth/login", json={"init_data": make_init_data(950003)})
    token = {"Authorization": f"Bearer {res.json()['session_token']}"}
    assert len(client.get("/api/history", headers=token).json()["items"]) == 3
    assert client.get("/api/uzum/orders", headers=token).json()["orders"]


def test_stage_page_is_served(client):
    res = client.get("/stage")
    assert res.status_code == 200 and "<html" in res.text.lower()
