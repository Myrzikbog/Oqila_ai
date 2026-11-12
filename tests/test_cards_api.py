"""Card API of the unified pipeline: generate, edit the copy, render, fix the lettering, old links, migration."""
import io
import json
import re
import sqlite3
import subprocess
import sys
import types
from pathlib import Path

import pytest
from PIL import Image

from conftest import auth, login, media_qs
from services import ai_service as ai_module
from test_cards import BAD1, GOOD, _png, scripted

ROOT = Path(__file__).resolve().parent.parent

TEXT_ANSWER = {
    "title": "🌸 Расписное блюдо «Риштан»", "description": "• Ручная роспись\n• Безопасная глазурь", "price_tag": "💰 Цена: 999 000 сум",
    "hashtags": ["#блюдо"], "marketing_tip": "Совет",
    "info": {"title": "Расписное блюдо «Риштан»", "tagline": "Нарядный · Яркий", "benefits": ["Ручная роспись", "Безопасная глазурь", "Для плова"],
             "badge": "", "uses": []},
}


def online(monkeypatch, reads, pictures=None, text=TEXT_ANSWER):
    """The application's AI service with a scripted text model, image model and text reader."""
    service, log = scripted(monkeypatch, reads, pictures, service=ai_module.ai_service)
    texts = []

    async def generate(kind, models, contents, config, accept=None):
        assert kind == "text"
        texts.append(config.system_instruction)
        return types.SimpleNamespace(text=json.dumps(text, ensure_ascii=False))

    monkeypatch.setattr(service, "_generate", generate)
    return log, texts


def _generate(client, who, style, facts="", status=200, **extra):
    data = {"note": "Расписное блюдо", "photoshoot_style": style, "info_text": facts, "lang": "ru", **extra}
    res = client.post("/api/generate-card", data=data, files={"image": ("plate.png", _png(), "image/png")}, headers=auth(who))
    assert res.status_code == status, res.text
    return res.json()


def _history_item(client, who, card_id):
    return next(i for i in client.get("/api/history", headers=auth(who)).json()["items"] if i["id"] == card_id)


# --- generate -----------------------------------------------------------------------------------

def test_generate_draws_the_picture_and_returns_copy_and_verification(client, monkeypatch):
    log, texts = online(monkeypatch, [GOOD])
    who = login(client, tg_id=971001)
    res = _generate(client, who, "info_dark_pills")
    assert res["studio_photo_url"].startswith("data:image/jpeg") and res["verification"]["verified"] is True
    assert res["copy"]["title"] == "Расписное блюдо «Риштан»" and res["copy"]["bullets"] == ["Ручная роспись", "Безопасная глазурь", "Для плова"]
    assert res["aspect"] == "3:4" and res["has_source"] is True and res["id"]
    for gone in ("poster", "poster_url", "poster_has_scene", "display", "info"):
        assert gone not in res
    photo = client.get(f"/api/cards/{res['id']}/photo", headers=auth(who))
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/jpeg"
    item = _history_item(client, who, res["id"])
    assert item["copy"]["title"] == res["copy"]["title"] and item["verification"]["verified"] is True and item["aspect"] == "3:4"
    for gone in ("has_poster", "poster_url", "poster_config", "poster_has_scene", "info_config"):
        assert gone not in item
    assert "max 32 chars" in texts[0], "the text model is told the limits of the format"


def test_the_price_on_the_picture_is_the_form_price_not_the_ai_price(client, monkeypatch):
    log, _ = online(monkeypatch, [[["Расписное блюдо «Риштан»"], ["380 000 сум"], ["450 000 сум"], ["−16%"]]])
    who = login(client, tg_id=971002)
    res = _generate(client, who, "promo_sale", desired_price="380000", old_price="450000")
    assert (res["copy"]["price"], res["copy"]["old_price"], res["copy"]["discount"]) == ("380 000 сум", "450 000 сум", "−16%")
    assert "999 000" not in log[0]["prompt"] and '"380 000 сум"' in log[0]["prompt"]
    assert res["aspect"] == "1:1" and Image.open(io.BytesIO(client.get(f"/api/cards/{res['id']}/photo", headers=auth(who)).content)).size == (1080, 1080)
    no_price = _generate(client, who, "info_table", "Диаметр: 32 см", text_only="true", desired_price="380000")
    assert no_price["copy"]["price"] == "" and no_price["copy"]["specs"] == [{"name": "Диаметр", "value": "32 см"}]


def test_text_only_stops_before_the_picture(client, monkeypatch):
    log, _ = online(monkeypatch, [])
    who = login(client, tg_id=971003)
    res = _generate(client, who, "poster_magazine", text_only="true", desired_price="240000")
    assert res["studio_photo_url"] is None and res["verification"] is None and log == []
    assert res["copy"]["price"] == "240 000 сум" and res["id"] and res["has_source"]
    assert client.get(f"/api/cards/{res['id']}/photo", headers=auth(who)).status_code == 404


def test_branding_goes_into_the_prompt(client, monkeypatch):
    log, _ = online(monkeypatch, [GOOD])
    who = login(client, tg_id=971004)
    client.put("/api/brand", json={"brand_name": "Silk House", "brand_color": "#7c3aed", "brand_contact": "+998 90 111 22 33"}, headers=auth(who))
    client.post("/api/brand/logo", files={"logo": ("l.png", _png(), "image/png")}, headers=auth(who))
    res = _generate(client, who, "poster_showcase")
    assert res["copy"]["brand_name"] == "Silk House" and res["copy"]["contact"] == "+998 90 111 22 33"
    assert "violet (#7c3aed)" in log[0]["prompt"] and log[0]["refs"] == 2 and '"Silk House"' in log[0]["prompt"]


def test_no_picture_is_an_honest_result_not_a_server_drawing(client, monkeypatch):
    online(monkeypatch, [], pictures=[])
    who = login(client, tg_id=971005)
    res = _generate(client, who, "story_order")
    assert res["studio_photo_url"] is None and res["render_error"] == "unavailable" and res["copy"]["title"]
    assert res["id"], "the text is real, so the card is kept and can be rendered later"


def test_problems_are_reported_with_the_picture(client, monkeypatch):
    online(monkeypatch, [BAD1, BAD1, BAD1])
    who = login(client, tg_id=971006)
    res = _generate(client, who, "info_dark_pills")
    assert res["verification"]["verified"] is False and res["image_calls"] == 3 and res["studio_photo_url"]
    assert {"expected": "Безопасная глазурь", "found": "Безогсасная глазурь"} in res["verification"]["problems"]


def test_offline_generation_is_flagged_and_not_saved(client):
    who = login(client, tg_id=971007)
    res = _generate(client, who, "info_table", "Диаметр: 32 см")
    assert res["ai_fallback"] == "no_key" and res["id"] is None and res["studio_photo_url"] is None
    assert client.get("/api/history", headers=auth(who)).json()["items"] == [], "sample text never lands in the history"


def test_ai_failure_is_reported_instead_of_passing_sample_text_as_real(client, monkeypatch):
    service = ai_module.ai_service
    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")

    async def quota(kind, models, contents, config, accept=None):
        raise RuntimeError("402 RESOURCE_EXHAUSTED. Your prepayment credits are depleted.")

    monkeypatch.setattr(service, "_generate", quota)
    who = login(client, tg_id=971008)
    res = _generate(client, who, "info_table")
    assert res["ai_fallback"] == "quota" and res["id"] is None
    assert client.get("/api/history", headers=auth(who)).json()["items"] == []


def test_clean_uzum_card_keeps_the_original_for_later(client, fake_ai):
    from services.database import DB_PATH

    who = login(client, tg_id=971009)
    res = _generate(client, who, "uzum_clean")
    assert "copy" not in res or res["copy"] is None
    item = _history_item(client, who, res["id"])
    assert item["photoshoot_style"] == "uzum_clean" and item["copy"] is None and item["has_source"] is True
    with sqlite3.connect(DB_PATH) as conn:
        ref = conn.execute("SELECT source_photo_url FROM generated_cards WHERE id = ?", (res["id"],)).fetchone()[0]
    assert ref and ref.startswith("file:source/")


# --- copy, render, fix-text ---------------------------------------------------------------------------

def test_copy_endpoint_cleans_the_sellers_text_without_ai(client, monkeypatch):
    log, texts = online(monkeypatch, [])
    alice, bob = login(client, tg_id=971010), login(client, tg_id=971011)
    card = _generate(client, alice, "promo_sale", text_only="true")
    calls = len(texts)
    body = {"copy": {"title": "Новая цена на блюдо ручной работы из Риштана", "price": "199000", "old_price": "240 000 сум", "bullets": ["лишнее"]}}
    res = client.post(f"/api/cards/{card['id']}/copy", json=body, headers=auth(alice))
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["copy"]["price"] == "199 000 сум" and out["copy"]["discount"] == "−17%" and out["copy"]["bullets"] == []
    assert len(out["copy"]["title"]) <= 32 and out["too_long"] == ["title"] and len(texts) == calls, "no AI call"
    assert client.post(f"/api/cards/{card['id']}/copy", json=body, headers=auth(bob)).status_code == 404
    assert client.post(f"/api/cards/{card['id']}/copy", json=body).status_code == 401


def test_copy_endpoint_rewrites_with_one_text_call(client, monkeypatch):
    log, texts = online(monkeypatch, [])
    who = login(client, tg_id=971012)
    card = _generate(client, who, "info_callouts", text_only="true")
    res = client.post(f"/api/cards/{card['id']}/copy", json={"style": "info_table", "info_text": "Вес: 1,2 кг"}, headers=auth(who))
    assert res.status_code == 200 and res.json()["copy"]["specs"] == [{"name": "Вес", "value": "1,2 кг"}]
    assert len(texts) == 2 and log == [], "a text call, never an image call"
    plain = _generate(client, who, "flat_lay")
    assert client.post(f"/api/cards/{plain['id']}/copy", json={}, headers=auth(who)).status_code == 400


def test_render_draws_the_approved_text_in_any_style(client, monkeypatch):
    log, _ = online(monkeypatch, [])
    alice, bob = login(client, tg_id=971013), login(client, tg_id=971014)
    card = _generate(client, alice, "info_callouts", text_only="true")
    log = scripted(monkeypatch, [[["Новое название"], ["199 000 сум"], ["@shop"]]], service=ai_module.ai_service)[1]
    body = {"copy": {"title": "Новое название", "price": 199000, "contact": "@shop", "bullets": ["не для этого формата"]},
            "style": "poster_minimal", "aspect": "1:1"}
    res = client.post(f"/api/cards/{card['id']}/render", json=body, headers=auth(alice))
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["photoshoot_style"] == "poster_minimal" and out["aspect"] == "1:1" and out["verification"]["verified"] is True
    assert out["copy"]["title"] == "Новое название" and out["copy"]["bullets"] == [] and out["version"]
    assert out["photo_url"] == out["studio_photo_url"] and out["photo_url"].startswith(f"/api/cards/{card['id']}/photo?v=")
    assert '"Новое название"' in log[0]["prompt"] and "не для этого формата" not in log[0]["prompt"] and log[0]["refs"] == 1
    photo = client.get(out["photo_url"], headers=auth(alice))
    assert Image.open(io.BytesIO(photo.content)).size == (1080, 1080)
    item = _history_item(client, alice, card["id"])
    assert item["copy"]["title"] == "Новое название" and item["photoshoot_style"] == "poster_minimal" and item["aspect"] == "1:1"
    assert client.post(f"/api/cards/{card['id']}/render", json=body, headers=auth(bob)).status_code == 404
    assert client.post(f"/api/cards/{card['id']}/render", json=body).status_code == 401
    assert client.post(f"/api/cards/{card['id']}/render", json={"copy": {"title": " "}}, headers=auth(alice)).status_code == 400


def test_render_rules(client, monkeypatch, fake_ai):
    who = login(client, tg_id=971015)
    plain = _generate(client, who, "flat_lay")
    assert client.post(f"/api/cards/{plain['id']}/render", json={}, headers=auth(who)).status_code == 400
    online(monkeypatch, [])
    card = _generate(client, who, "info_table", text_only="true")
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "mock")
    off = client.post(f"/api/cards/{card['id']}/render", json={}, headers=auth(who))
    assert off.status_code == 503 and "временно недоступна" in off.json()["detail"], "AI is off: an honest error"
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    scripted(monkeypatch, [], pictures=[], service=ai_module.ai_service)
    assert client.post(f"/api/cards/{card['id']}/render", json={}, headers=auth(who)).status_code == 503, "no picture, no substitute"
    assert _history_item(client, who, card["id"])["has_studio_photo"] is False


def test_old_info_photo_route_and_field_names_still_work(client, monkeypatch):
    online(monkeypatch, [])
    who = login(client, tg_id=971016)
    card = _generate(client, who, "info_dark_list", text_only="true")
    log = scripted(monkeypatch, [[["Старый клиент"], ["Один"], ["Вес: 1,2 кг"]]], service=ai_module.ai_service)[1]
    body = {"title": "Старый клиент", "benefits": ["Один"], "specs": [{"name": "Вес", "value": "1,2 кг"}], "style": "info_dark_list"}
    res = client.post(f"/api/cards/{card['id']}/info-photo", json=body, headers=auth(who))
    assert res.status_code == 200, res.text
    assert res.json()["info"]["title"] == "Старый клиент" and res.json()["copy"]["bullets"] == ["Один"]
    assert res.json()["verification"]["verified"] is True


def test_fix_text_edits_the_stored_picture(client, monkeypatch):
    online(monkeypatch, [BAD1, BAD1, BAD1])
    who, other = login(client, tg_id=971017), login(client, tg_id=971018)
    card = _generate(client, who, "info_dark_pills")
    assert card["verification"]["verified"] is False
    log = scripted(monkeypatch, [GOOD], service=ai_module.ai_service)[1]
    res = client.post(f"/api/cards/{card['id']}/fix-text", json={}, headers=auth(who))
    assert res.status_code == 200, res.text
    assert res.json()["verification"]["verified"] is True and len(log) == 1 and log[0]["refs"] == 1
    assert 'with exactly "Безопасная глазурь"' in log[0]["prompt"], "by default the reported problems are fixed"
    assert _history_item(client, who, card["id"])["verification"]["verified"] is True
    # the seller can name the wrong line themselves; nothing to fix is a 400
    log = scripted(monkeypatch, [GOOD], service=ai_module.ai_service)[1]
    named = client.post(f"/api/cards/{card['id']}/fix-text", json={"problems": [{"expected": "Для плова", "found": "Для плава"}]}, headers=auth(who))
    assert named.status_code == 200 and 'replace text "Для плава" with exactly "Для плова"' in log[0]["prompt"]
    assert client.post(f"/api/cards/{card['id']}/fix-text", json={}, headers=auth(who)).status_code == 400
    assert client.post(f"/api/cards/{card['id']}/fix-text", json={}, headers=auth(other)).status_code == 404


def test_render_and_fix_count_against_the_ai_limit(client, monkeypatch):
    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "2")
    online(monkeypatch, [BAD1, BAD1, BAD1, BAD1, BAD1, BAD1])
    who = login(client, tg_id=971019)
    card = _generate(client, who, "info_dark_pills")
    assert client.post(f"/api/cards/{card['id']}/render", json={}, headers=auth(who)).status_code == 200
    assert client.post(f"/api/cards/{card['id']}/render", json={}, headers=auth(who)).status_code == 429
    assert client.post(f"/api/cards/{card['id']}/fix-text", json={}, headers=auth(who)).status_code == 429
    limits = client.get("/api/limits", headers=auth(who)).json()
    assert limits["generate_card"]["used"] == 2


# --- old links, downloads, registry ---------------------------------------------------------------------

def test_old_poster_links_are_redirected(client, monkeypatch):
    online(monkeypatch, [GOOD])
    who = login(client, tg_id=971020)
    card = _generate(client, who, "info_dark_pills")
    qs = media_qs(client, who)
    res = client.get(f"/api/cards/{card['id']}/poster.png?{qs}", follow_redirects=False)
    assert res.status_code == 301 and res.headers["location"] == f"/api/cards/{card['id']}/photo?{qs}"
    assert client.get(f"/api/cards/{card['id']}/poster.png?{qs}").status_code == 200
    assert client.post(f"/api/cards/{card['id']}/poster", json={"title": "x"}, headers=auth(who)).status_code in (404, 405)


def test_download_has_a_file_name_with_the_real_extension(client, monkeypatch):
    online(monkeypatch, [GOOD])
    who = login(client, tg_id=971021)
    card = _generate(client, who, "info_dark_pills")
    plain = client.get(f"/api/cards/{card['id']}/photo?{media_qs(client, who)}")
    assert "content-disposition" not in plain.headers
    res = client.get(f"/api/cards/{card['id']}/photo?download=1&{media_qs(client, who)}")
    assert res.headers["content-disposition"] == f'attachment; filename="oqila-{card["id"]}.jpg"'
    assert res.content[:3] == b"\xff\xd8\xff"


def test_registry_describes_fields_and_limits(client):
    reg = client.get("/api/photoshoot-presets").json()
    assert "layouts" not in reg and "palettes" not in reg and "default_palette" not in reg
    assert [g["id"] for g in reg["groups"][:2]] == ["uzum", "info"] and [g["tier"] for g in reg["groups"][:2]] == ["main", "main"]
    assert not any("без ИИ" in g["hint_ru"] or "AIsiz" in g["hint_uz"] for g in reg["groups"])
    styles = {s["id"]: s for s in reg["styles"]}
    for sid in ("poster_showcase", "poster_magazine", "poster_minimal", "promo_sale", "promo_new", "promo_limited", "story_order", "market_callouts"):
        assert styles[sid]["kind"] == "ai_text" and "layout" not in styles[sid] and "prompt" not in styles[sid]
    sale = styles["promo_sale"]
    assert sale["fields"]["title"] == {"count": 1, "limit": 32} and set(sale["fields"]) == {"title", "discount", "price", "old_price", "deadline"}
    assert sale["limits"]["bullet"] == 28 and sale["aspects"] == ["3:4", "1:1", "4:5", "9:16"] and sale["max_blocks"] == 6
    assert styles["info_table"]["fields"]["specs"] == {"count": 5, "limit_name": 18, "limit_value": 22}
    assert styles["story_order"]["aspects"] == ["9:16"] and styles["story_order"]["max_blocks"] == 4
    assert "Без ИИ" not in json.dumps(reg, ensure_ascii=False) and "fields" not in styles["flat_lay"]
    assert {s["id"] for s in reg["styles"] if s["group"] == "uzum"} == {"uzum_clean", "uzum_gradient"}


def test_poster_render_limit_is_gone():
    from services.rate_limit import LIMITS

    assert "poster_render" not in LIMITS and "card_copy" in LIMITS


# --- the server does not draw text ---------------------------------------------------------------------

def test_no_server_side_text_drawing_outside_shipping_labels():
    """Marketing pictures get their text from the AI only. The one place that may draw text is the FBS shipping
    label in uzum_service.py (a barcode document for a thermal printer). scripts/legacy_poster.py is the old
    renderer kept for the one-off migration: nothing in the application imports it."""
    drawing = re.compile(r"\bImageFont\b|\.text\(|\.multiline_text\(|\.textbbox\(|\.textlength\(")
    runtime = [ROOT / "main.py", *sorted((ROOT / "services").glob("*.py"))]
    offenders = [p.name for p in runtime if p.name != "uzum_service.py" and drawing.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
    for path in runtime:
        source = path.read_text(encoding="utf-8")
        assert "legacy_poster" not in source and "services.poster" not in source, path.name
    assert not (ROOT / "services" / "poster.py").exists() and not (ROOT / "assets" / "fonts").exists()


# --- migration of old posters ----------------------------------------------------------------------------

def _insert_legacy(conn, user_id, title, poster=None, info=None, studio=None, source=None):
    cur = conn.execute(
        "INSERT INTO generated_cards (title, user_id, photoshoot_style, lang, poster_config, info_config, studio_photo_url, source_photo_url) "
        "VALUES (?, ?, 'poster_showcase', 'ru', ?, ?, ?, ?)",
        (title, user_id, json.dumps(poster, ensure_ascii=False) if poster else None,
         json.dumps(info, ensure_ascii=False) if info else None, studio, source),
    )
    return cur.lastrowid


def test_poster_migration_bakes_pictures_and_is_idempotent(client):
    from services.database import DB_PATH
    from services.media_storage import media_dir, resolve_photo, store_bytes

    who = login(client, tg_id=971030)
    uid = who["user_id"]
    poster = {"layout": "sale", "aspect": "1:1", "palette": "dark", "lang": "ru", "title": "Новая цена!", "price": "199 000 сум",
              "old_price": "240 000 сум", "badge_text": "-17%", "bullets": ["Ручная работа"], "contact": "@shop"}
    scene, source = store_bytes("cards", _png((10, 90, 90)), "png"), store_bytes("source", _png(), "png")
    with sqlite3.connect(DB_PATH) as conn:
        with_scene = _insert_legacy(conn, uid, "scene", poster=poster, studio=scene)
        offline = _insert_legacy(conn, uid, "offline", poster={**poster, "layout": "story", "aspect": "9:16"}, source=source)
        already_ai = _insert_legacy(conn, uid, "ai", poster=poster, info={"title": "AI", "benefits": ["a"], "verified": True}, studio=store_bytes("cards", _png(), "png"))
        untouched = _insert_legacy(conn, uid, "plain")

    env = {**__import__("os").environ}
    cmd = [sys.executable, str(ROOT / "scripts" / "migrate_posters.py")]
    dry = subprocess.run(cmd + ["--dry-run"], capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert dry.returncode == 0 and "baked into pictures: 2" in dry.stdout and "cleared (already AI pictures): 1" in dry.stdout, dry.stdout + dry.stderr
    with sqlite3.connect(DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM generated_cards WHERE poster_config IS NOT NULL AND user_id = ?", (uid,)).fetchone()[0] == 3, "dry run changes nothing"
    assert resolve_photo(scene)

    real = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert real.returncode == 0 and "baked into pictures: 2" in real.stdout, real.stdout + real.stderr
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = {r["id"]: r for r in conn.execute("SELECT * FROM generated_cards WHERE user_id = ?", (uid,))}
    assert all(r["poster_config"] is None for r in rows.values())
    baked = rows[with_scene]
    assert baked["studio_photo_url"] != scene and resolve_photo(scene) is None, "the bare scene is replaced by the baked poster"
    assert Image.open(resolve_photo(baked["studio_photo_url"])).size == (1080, 1080)
    info = json.loads(baked["info_config"])
    assert info["copy"]["legacy"] is True and info["copy"]["title"] == "Новая цена!" and info["copy"]["price"] == "199 000 сум"
    assert info["copy"]["old_price"] == "240 000 сум" and info["copy"]["badge"] == "-17%" and info["aspect"] == "1:1"
    assert Image.open(resolve_photo(rows[offline]["studio_photo_url"])).size == (1080, 1920), "offline cards are baked from the seller's photo"
    assert resolve_photo(source), "the seller's own photo stays for future renders"
    assert json.loads(rows[already_ai]["info_config"])["title"] == "AI", "AI cards only lose the poster config"
    assert rows[untouched]["studio_photo_url"] is None and rows[untouched]["info_config"] is None

    # the migrated card is an ordinary card for the API
    item = _history_item(client, who, with_scene)
    assert item["copy"]["legacy"] is True and item["studio_photo_url"] == f"/api/cards/{with_scene}/photo"
    assert client.get(f"/api/cards/{with_scene}/poster.png?{media_qs(client, who)}").status_code == 200
    legacy_ai = _history_item(client, who, already_ai)
    assert legacy_ai["copy"]["bullets"] == ["a"] and legacy_ai["verification"]["verified"] is True, "old flat info rows are still readable"

    again = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(ROOT))
    assert again.returncode == 0 and "baked into pictures: 0" in again.stdout and "cleared (already AI pictures): 0" in again.stdout
    assert media_dir().exists()
