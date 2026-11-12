"""Critical fixes of the master plan, phase 1: admin login, AI budget, atomic limits, fallbacks, uploads, tokens."""
import asyncio
import io
import re
import sqlite3
import threading
import time
import types
from pathlib import Path

import pytest
from PIL import Image

from conftest import ADMIN_KEY, auth, login, media_qs

ROOT = Path(__file__).resolve().parent.parent


def _png(size=(64, 64), color=(200, 40, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


# --- 1.1 administrator signs in twice ---------------------------------------------------------

def test_admin_can_sign_in_again(client, monkeypatch):
    from services.database import upsert_user

    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "810001")
    first = upsert_user(tg_id=810001, tg_first_name="Boss")
    second = upsert_user(tg_id=810001, tg_first_name="Boss")
    assert first["user_id"] and first["user_id"] == second["user_id"]
    assert second["is_admin"] == 1
    assert login(client, tg_id=810001)["user_id"] == first["user_id"]
    assert login(client, tg_id=810001)["profile"]["is_admin"] is True


def test_existing_user_becomes_admin_when_listed(monkeypatch):
    from services.database import upsert_user

    before = upsert_user(tg_id=810002)
    assert not before["is_admin"]
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "810002")
    after = upsert_user(tg_id=810002)
    assert after["user_id"] == before["user_id"] and after["is_admin"] == 1


# --- 1.2 guests per IP, bot photos ------------------------------------------------------------

def test_sixth_guest_from_one_ip_is_refused(client, monkeypatch):
    monkeypatch.setenv("GUESTS_PER_IP_PER_HOUR", "5")
    monkeypatch.setenv("TRUSTED_PROXIES", "testclient")
    ip = {"X-Real-IP": "203.0.113.7"}
    tokens = []
    for _ in range(5):
        res = client.post("/api/auth/login", json={}, headers=ip)
        assert res.status_code == 200
        tokens.append(res.json()["session_token"])
    assert client.post("/api/auth/login", json={}, headers=ip).status_code == 429
    # an existing guest keeps the account, and other addresses are not affected
    again = client.post("/api/auth/login", json={}, headers={**ip, "Authorization": f"Bearer {tokens[0]}"})
    assert again.status_code == 200
    assert client.post("/api/auth/login", json={}, headers={"X-Real-IP": "203.0.113.8"}).status_code == 200


def test_x_real_ip_is_ignored_from_untrusted_peers(client, monkeypatch):
    from main import client_ip

    monkeypatch.setenv("TRUSTED_PROXIES", "127.0.0.1")
    request = types.SimpleNamespace(client=types.SimpleNamespace(host="198.51.100.9"), headers={"x-real-ip": "1.2.3.4"})
    assert client_ip(request) == "198.51.100.9"
    request.client.host = "127.0.0.1"
    assert client_ip(request) == "1.2.3.4"


def _photo_update(tg_id: int) -> dict:
    return {"photo": [{"file_id": "f1"}], "from": {"id": tg_id, "first_name": "T"}, "chat": {"id": tg_id}}


def _bot_with_photo(monkeypatch):
    from services.telegram_service import telegram_service

    async def download(file_id):
        return _png()

    monkeypatch.setattr(telegram_service, "download_telegram_file", download)
    return telegram_service


def test_bot_photo_respects_the_user_limit(client, monkeypatch, no_telegram_network, fake_ai):
    bot = _bot_with_photo(monkeypatch)
    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "1")
    login(client, tg_id=810010)
    asyncio.run(bot._handle_photo_message(_photo_update(810010), 810010, "https://app.example"))
    assert len(fake_ai) == 1 and "🎉" in no_telegram_network[-1]["text"]
    asyncio.run(bot._handle_photo_message(_photo_update(810010), 810010, "https://app.example"))
    assert len(fake_ai) == 1, "the AI is not called once the limit is spent"
    assert "Слишком много" in no_telegram_network[-1]["text"] or "ko'p so'rov" in no_telegram_network[-1]["text"]


def test_bot_never_sends_the_sample_post(client, monkeypatch, no_telegram_network):
    bot = _bot_with_photo(monkeypatch)  # AI_MODE=mock
    asyncio.run(bot._handle_photo_message(_photo_update(810011), 810011, "https://app.example"))
    last = no_telegram_network[-1]["text"]
    assert "AI" in last and "Anor" not in last and "Анор" not in last


# --- 1.3 atomic reservations -----------------------------------------------------------------

def test_parallel_reservations_never_exceed_the_limit(client, monkeypatch):
    from services.rate_limit import LimitExceeded, reserve

    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "3")
    uid = login(client, tg_id=810020)["user_id"]
    results, barrier = [], threading.Barrier(10)

    def worker():
        barrier.wait()
        try:
            results.append(reserve("generate_card", uid, "ru"))
        except LimitExceeded:
            results.append(None)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len([r for r in results if r]) == 3


def test_failed_attempts_are_free_but_bounded(client, monkeypatch):
    from services.rate_limit import LimitExceeded, finish, limits_status, reserve

    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "2")
    uid = login(client, tg_id=810021)["user_id"]
    for _ in range(5):
        finish(reserve("generate_card", uid), ok=False)
    assert limits_status(uid)["generate_card"]["hour"]["used"] == 0, "failures do not spend the user's quota"
    finish(reserve("generate_card", uid), ok=True)
    with pytest.raises(LimitExceeded):  # 6 attempts = 3 x the limit of 2
        reserve("generate_card", uid)


def test_limits_endpoint(client, monkeypatch):
    from services.rate_limit import finish, reserve

    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "1")
    who = login(client, tg_id=810022)
    assert client.get("/api/limits").status_code == 401
    fresh = client.get("/api/limits", headers=auth(who)).json()
    assert fresh["generate_card"]["used"] == 0 and fresh["generate_card"]["resets_at"] is None and "legal_qa" in fresh
    finish(reserve("generate_card", who["user_id"]), ok=True)
    full = client.get("/api/limits", headers=auth(who)).json()["generate_card"]
    assert full["used"] == 1 and full["hour"] == {"used": 1, "limit": 1} and full["resets_at"]


def test_a_crashed_generation_does_not_give_free_retries(client, monkeypatch, fake_ai):
    from services import ai_service as ai_module

    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "1")
    who = login(client, tg_id=810023)

    async def crash(*a, **k):
        raise KeyboardInterrupt  # not an Exception: nothing in the endpoint catches it

    monkeypatch.setattr(ai_module.ai_service, "generate_product_card", crash)
    for _ in range(3):
        with pytest.raises(BaseException):
            client.post("/api/generate-card", data={"note": "x"}, headers=auth(who))
    assert client.post("/api/generate-card", data={"note": "x"}, headers=auth(who)).status_code == 429


def test_every_gemini_request_is_counted(monkeypatch):
    from services import ai_service as ai_module
    from services.rate_limit import ai_calls_today, global_ai_budget_exhausted

    service = ai_module.ai_service

    def generate_content(model, contents, config):
        if model == "first":
            raise RuntimeError("down")
        return types.SimpleNamespace(text="ok")

    monkeypatch.setattr(service, "_client", types.SimpleNamespace(models=types.SimpleNamespace(generate_content=generate_content)))
    before = ai_calls_today()
    res = asyncio.run(service._generate("text", ["first", "second"], "hi", None))
    assert res.text == "ok" and ai_calls_today() == before + 2, "the failed attempt was a real request too"
    monkeypatch.setenv("AI_GLOBAL_DAILY_LIMIT", str(before + 2))
    assert global_ai_budget_exhausted()
    monkeypatch.setenv("AI_GLOBAL_DAILY_LIMIT", "0")
    assert not global_ai_budget_exhausted()


# --- 1.4 / 1.5 fallbacks -----------------------------------------------------------------------

def test_forced_mock_is_flagged_and_not_saved(client, monkeypatch, fake_ai):
    monkeypatch.setenv("AI_GLOBAL_DAILY_LIMIT", "1")
    from services.rate_limit import record_ai_call

    record_ai_call("text", "test")
    who = login(client, tg_id=810030)
    res = client.post("/api/generate-card", data={"note": "x"}, headers=auth(who)).json()
    assert res["ai_fallback"] == "quota" and res["id"] is None
    with sqlite3.connect(__import__("services.database", fromlist=["DB_PATH"]).DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM generated_cards WHERE user_id = ?", (who["user_id"],)).fetchone()[0] == 0
    assert fake_ai == []


def test_text_model_failure_keeps_the_picture(client, monkeypatch):
    from services import ai_service as ai_module
    from services.imaging import finalize_card, to_data_url

    service = ai_module.ai_service
    photo = to_data_url(finalize_card(_png((900, 1200))))

    async def generate(kind, models, contents, config, accept=None):
        raise RuntimeError("503 text model overloaded")

    async def studio_photo(**kwargs):
        return photo

    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")
    monkeypatch.setattr(service, "_generate", generate)
    monkeypatch.setattr(service, "generate_studio_photo", studio_photo)
    who = login(client, tg_id=810031)
    res = client.post("/api/generate-card", data={"note": "Ваза", "photoshoot_style": "flat_lay"},
                      files={"image": ("v.png", _png(), "image/png")}, headers=auth(who)).json()
    assert res["studio_photo_url"] == photo, "the finished picture survives"
    assert res["ai_fallback"] == "error" and res["ai_fallback_scope"] == "text"
    assert res["description"] == "" and "Анор" not in res["title"], "no sample text next to a real picture"
    assert res["id"], "a real picture is saved"


def test_both_failing_gives_a_plain_fallback(client, monkeypatch):
    from services import ai_service as ai_module

    service = ai_module.ai_service

    async def generate(kind, models, contents, config, accept=None):
        raise RuntimeError("429 quota")

    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")
    monkeypatch.setattr(service, "_generate", generate)
    who = login(client, tg_id=810032)
    res = client.post("/api/generate-card", data={"note": "Ваза"}, headers=auth(who)).json()
    assert res["ai_fallback"] == "quota" and res["id"] is None


def test_model_names_come_from_the_environment(monkeypatch):
    from services.ai_service import AIService

    monkeypatch.setenv("GEMINI_TEXT_MODEL", "t1")
    monkeypatch.setenv("GEMINI_TEXT_FALLBACK_MODEL", "t2")
    monkeypatch.setenv("GEMINI_LEGAL_MODEL", "l1")
    assert AIService._text_models() == ["t1", "t2"]
    assert AIService._legal_models() == ["l1", "t1", "t2"]
    for path in (ROOT / "services").glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if '"gemini-' in line and not line.lstrip().startswith(("#", '"""')):
                assert "os.getenv(" in line, f"hard-coded model in {path.name}: {line.strip()}"


# --- 1.6 uploads ---------------------------------------------------------------------------------

def test_decompression_bomb_is_rejected_before_decoding(client):
    buf = io.BytesIO()
    Image.new("1", (10000, 10000)).save(buf, format="PNG")  # 100 megapixels in a few kilobytes
    who = login(client, tg_id=810040)
    started = time.monotonic()
    res = client.post("/api/generate-card", files={"image": ("bomb.png", buf.getvalue(), "image/png")}, headers=auth(who))
    assert res.status_code == 413 and time.monotonic() - started < 2


def test_oversized_upload_is_413(client):
    who = login(client, tg_id=810041)
    big = b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024 - 2)  # 10 MB + 1 byte
    res = client.post("/api/generate-card", files={"image": ("big.jpg", big, "image/jpeg")}, headers=auth(who))
    assert res.status_code == 413


def test_type_comes_from_the_bytes_not_the_header(client, fake_ai):
    who = login(client, tg_id=810042)
    lying = client.post("/api/generate-card", files={"image": ("x.png", b"<html>", "image/png")}, headers=auth(who))
    assert lying.status_code == 415
    heic = client.post("/api/generate-card", data={"lang": "ru"},
                       files={"image": ("x.heic", b"\x00\x00\x00\x18ftypheic" + b"0" * 64, "")}, headers=auth(who))
    assert heic.status_code == 415 and "HEIC" in heic.json()["detail"]
    honest = client.post("/api/generate-card", files={"image": ("x.bin", _png(), "application/octet-stream")}, headers=auth(who))
    assert honest.status_code == 200 and fake_ai[-1]["has_image"]


def test_the_ai_gets_a_normalized_jpeg(client, monkeypatch):
    from services import ai_service as ai_module

    seen = {}

    async def spy(**kwargs):
        seen.update(kwargs)
        return {"title": "t", "description": "", "price_tag": "", "hashtags": [], "marketing_tip": ""}

    monkeypatch.setattr(ai_module.ai_service, "generate_product_card", spy)
    who = login(client, tg_id=810043)
    client.post("/api/generate-card", files={"image": ("x.png", _png((4000, 3000)), "image/png")}, headers=auth(who))
    img = Image.open(io.BytesIO(seen["image_bytes"]))
    assert img.format == "JPEG" and max(img.size) == 2048 and seen["image_mime"] == "image/jpeg"


# --- 1.8 legal assistant and empty names ------------------------------------------------------

@pytest.mark.parametrize("name", ["  ", "", None])
def test_blank_name_does_not_break_the_legal_assistant(client, name):
    who = login(client, tg_id=810050)
    res = client.post("/api/legal-qa", json={"question": "Как открыть ЯТТ?", "user_profile": {"name": name}}, headers=auth(who))
    assert res.status_code == 200 and res.json()["ai_fallback"] == "no_key"


def test_blank_name_with_a_real_model(monkeypatch):
    from services import ai_service as ai_module

    service = ai_module.ai_service
    seen = {}

    async def generate(kind, models, contents, config, accept=None):
        seen["system"] = config.system_instruction
        return types.SimpleNamespace(text="answer")

    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")
    monkeypatch.setattr(service, "_generate", generate)
    answer, reason = asyncio.run(service.legal_qa("Вопрос?", "ru", {"name": "   "}))
    assert answer == "answer" and reason is None and "Предпринимательница" in seen["system"]


# --- 1.9 other backend bugs ---------------------------------------------------------------------

def test_admin_key_in_chat_is_a_temporary_session(client, monkeypatch):
    from services import telegram_service as tg_module
    from services.database import get_user_by_tg_id, upsert_user
    from services.telegram_service import telegram_service

    upsert_user(tg_id=810060)
    clock = {"now": 1000.0}
    monkeypatch.setattr(tg_module.time, "monotonic", lambda: clock["now"])
    assert not telegram_service.is_admin_user(810060)
    assert telegram_service.is_admin_user(810060, provided_key=ADMIN_KEY)
    assert telegram_service.is_admin_user(810060), "the session lasts for an hour"
    assert not get_user_by_tg_id(810060)["is_admin"], "nothing is written to the database"
    clock["now"] += 3601
    assert not telegram_service.is_admin_user(810060)


def test_admin_flag_is_set_in_the_panel_and_cache_expires(client, monkeypatch):
    from services import telegram_service as tg_module
    from services.database import set_user_admin
    from services.telegram_service import telegram_service

    who = login(client, tg_id=810061)
    guest = login(client)
    admin = {"X-Admin-Key": ADMIN_KEY}
    assert client.post(f"/api/admin/users/{who['user_id']}/toggle-admin").status_code == 403
    assert client.post(f"/api/admin/users/{guest['user_id']}/toggle-admin", headers=admin).status_code == 400
    assert not telegram_service.is_admin_user(810061)
    assert client.post(f"/api/admin/users/{who['user_id']}/toggle-admin", headers=admin).json()["is_admin"] is True
    assert telegram_service.is_admin_user(810061), "the panel drops the cached decision"

    clock = {"now": 5000.0}
    monkeypatch.setattr(tg_module.time, "monotonic", lambda: clock["now"])
    telegram_service.forget_admin_cache()
    assert telegram_service.is_admin_user(810061)
    set_user_admin(810061, False)  # changed behind the service's back
    assert telegram_service.is_admin_user(810061), "cached for up to five minutes"
    clock["now"] += 301
    assert not telegram_service.is_admin_user(810061)


def test_csv_cells_cannot_be_formulas():
    from services.csv_service import generate_cards_csv, generate_users_csv, safe_cell

    assert [safe_cell(v) for v in ("=1+1", "+7", "-2", "@x", "\tx", "\rx", "ok", 5)] == ["'=1+1", "'+7", "'-2", "'@x", "'\tx", "'\rx", "ok", 5]
    users = generate_users_csv([{"user_id": 1, "tg_id": 2, "name": "=HYPERLINK(\"http://evil\")", "tg_username": "@nick"}]).decode("utf-8-sig")
    assert "'=HYPERLINK" in users and ";=HYPERLINK" not in users
    cards = generate_cards_csv([{"id": 1, "title": "=cmd|' /C calc'!A0", "note": "+998"}]).decode("utf-8-sig")
    assert "'=cmd" in cards and ";=cmd" not in cards


def test_webhook_answers_at_once_and_ignores_repeats(app, monkeypatch):
    from fastapi.testclient import TestClient

    from services.session_service import get_webhook_secret
    from services.telegram_service import telegram_service

    handled = []
    release = asyncio.Event()

    async def slow_handle(update, default_app_url):
        handled.append(update["update_id"])
        await release.wait()

    monkeypatch.setattr(telegram_service, "handle_update", slow_handle)
    headers = {"X-Telegram-Bot-Api-Secret-Token": get_webhook_secret()}
    with TestClient(app) as live:  # keeps one event loop, so the background task really runs
        first = live.post("/api/telegram-webhook", json={"update_id": 77001}, headers=headers)
        assert first.status_code == 200, "answered while the handler is still waiting"
        repeat = live.post("/api/telegram-webhook", json={"update_id": 77001}, headers=headers)
        assert repeat.json().get("duplicate") is True
        live.post("/api/telegram-webhook", json={"update_id": 77002}, headers=headers)
        deadline = time.monotonic() + 2
        while len(handled) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        live.portal.call(release.set)
    assert handled == [77001, 77002]


def test_card_update_tells_missing_from_broken(client, monkeypatch, fake_ai):
    from services import database as db

    alice, bob = login(client, tg_id=810062), login(client, tg_id=810063)
    card_id = db.save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="", user_id=alice["user_id"])
    with pytest.raises(LookupError):
        db.update_card_render(card_id, bob["user_id"], None, {"title": "x"})
    with pytest.raises(LookupError):
        db.update_card_render(10**9, alice["user_id"], None, {"title": "x"})
    assert db.update_card_render(card_id, alice["user_id"], None, {"title": "x"}) == ""

    # a database error is an error, and the newly written picture is not left behind
    stored = []
    real_store = db.store_photo

    def tracking_store(value):
        ref = real_store(value)
        stored.append(ref)
        return ref

    monkeypatch.setattr(db, "store_photo", tracking_store)
    monkeypatch.setattr(db.json, "dumps", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    from services.imaging import finalize_card, to_data_url
    from services.media_storage import resolve_photo

    with pytest.raises(RuntimeError):
        db.update_card_render(card_id, alice["user_id"], to_data_url(finalize_card(_png())), {"title": "y"})
    assert stored and resolve_photo(stored[0]) is None


def test_unsaved_card_is_an_error_not_card_zero(client, monkeypatch, fake_ai):
    import main

    monkeypatch.setattr(main, "save_generated_card", lambda **k: 0)
    who = login(client, tg_id=810064)
    res = client.post("/api/generate-card", data={"note": "x"}, headers=auth(who))
    assert res.status_code == 500 and "/api/cards/0/" not in res.text


def test_files_are_deleted_only_after_the_commit(client, monkeypatch):
    from services import database as db
    from services.media_storage import resolve_photo, store_bytes

    who = login(client, tg_id=810065)
    ref = store_bytes("source", _png(), "png")
    card_id = db.save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="",
                                     user_id=who["user_id"], source_photo_url=ref)

    class Failing(db.ClosingConnection):
        def commit(self):
            raise sqlite3.OperationalError("database is locked")

    real = db.get_db_connection
    monkeypatch.setattr(db, "get_db_connection", lambda: sqlite3.connect(str(db.DB_PATH), factory=Failing))
    assert db.delete_history_item(card_id, who["user_id"]) is False
    assert db.clear_history(who["user_id"]) is False
    assert resolve_photo(ref), "the picture is still there: the card was not deleted"
    monkeypatch.setattr(db, "get_db_connection", real)
    assert db.delete_history_item(card_id, who["user_id"]) is True and resolve_photo(ref) is None


def test_uzum_keys_are_encrypted_at_rest(client):
    from services import database as db
    from services import secret_box

    who = login(client, tg_id=810066)
    db.save_uzum_settings(who["user_id"], api_key="live-secret-key-12345", is_connected=1, is_demo=0)
    with sqlite3.connect(db.DB_PATH) as conn:
        stored = conn.execute("SELECT api_key FROM uzum_settings WHERE user_id = ?", (who["user_id"],)).fetchone()[0]
    assert "live-secret" not in stored and secret_box.is_encrypted(stored)
    assert db.get_uzum_settings(who["user_id"], include_secret=True)["api_key"] == "live-secret-key-12345"
    public = db.get_uzum_settings(who["user_id"])
    assert "api_key" not in public and public["masked_key"] == "live••••••••2345"
    db.save_uzum_settings(who["user_id"], last_sync_at="2026-11-11T10:00:00")  # re-saving must not double-encrypt
    assert db.get_uzum_settings(who["user_id"], include_secret=True)["api_key"] == "live-secret-key-12345"
    assert who["user_id"] in db.get_connected_uzum_user_ids()


def test_plain_uzum_keys_are_encrypted_on_startup(client):
    from services import database as db
    from services import secret_box

    who = login(client, tg_id=810067)
    with sqlite3.connect(db.DB_PATH) as conn:
        conn.execute("INSERT OR REPLACE INTO uzum_settings (user_id, api_key, is_connected) VALUES (?, 'legacy-plain-key', 1)", (who["user_id"],))
    db.init_db(force=True)
    with sqlite3.connect(db.DB_PATH) as conn:
        stored = conn.execute("SELECT api_key FROM uzum_settings WHERE user_id = ?", (who["user_id"],)).fetchone()[0]
    assert secret_box.is_encrypted(stored) and secret_box.decrypt(stored) == "legacy-plain-key"


def test_search_treats_wildcards_literally(client):
    from services.database import get_history, save_generated_card

    who = login(client, tg_id=810068)
    for title in ("Скидка 50% на всё", "Скидка 500 сум", "a_b", "axb"):
        save_generated_card(title=title, description="", price_tag="", hashtags=[], marketing_tip="", user_id=who["user_id"])
    find = lambda q: sorted(i["title"] for i in get_history(search=q, user_id=who["user_id"]))  # noqa: E731
    assert find("50%") == ["Скидка 50% на всё"]
    assert find("a_b") == ["a_b"]
    assert find("%") == ["Скидка 50% на всё"] and find("\\") == []
    assert client.get("/api/history?search=_", headers=auth(who)).json()["total"] == 1


def test_connections_are_closed_after_a_with_block():
    from services.database import get_db_connection

    with get_db_connection() as conn:
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_uzum_locks_are_per_user():
    from services.uzum_service import uzum_service

    assert uzum_service._user_lock(1) is uzum_service._user_lock(1)
    assert uzum_service._user_lock(1) is not uzum_service._user_lock(2)


# --- 1.10 media tokens ----------------------------------------------------------------------------

def test_media_endpoints_take_only_media_tokens(client, monkeypatch):
    from services import session_service
    from services.database import save_generated_card
    from services.imaging import finalize_card, to_data_url

    alice, bob = login(client, tg_id=810070), login(client, tg_id=810071)
    card_id = save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="",
                                  studio_photo_url=to_data_url(finalize_card(_png())), user_id=alice["user_id"])
    url = f"/api/cards/{card_id}/photo"
    assert client.get(f"{url}?token={alice['session_token']}").status_code == 401, "no session tokens in URLs"
    assert client.get(f"{url}?mt={alice['session_token']}").status_code == 401
    assert client.get(f"{url}?{media_qs(client, alice)}").status_code == 200
    assert client.get(f"{url}?{media_qs(client, bob)}").status_code == 404
    assert client.get(url, headers=auth(alice)).status_code == 200, "fetch() with the header still works"

    expired = session_service.create_media_token(alice["user_id"], ttl_seconds=-1)
    assert client.get(f"{url}?mt={expired}").status_code == 401
    # a media token is not a session
    mt = session_service.create_media_token(alice["user_id"])
    assert client.get("/api/profile", headers={"Authorization": f"Bearer {mt}"}).status_code == 401
    assert session_service.verify_session_token(mt) is None
    assert client.post("/api/media-token").status_code == 401
    assert client.post("/api/media-token", headers=auth(alice)).json()["expires_in"] == 600
    assert client.get("/health").headers["referrer-policy"] == "no-referrer"
