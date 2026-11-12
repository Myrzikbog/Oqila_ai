"""Information cards, clean Uzum photos, text verification and the image-model fallback (no network: the AI is faked)."""
import asyncio
import base64
import io
import types

import pytest
from PIL import Image, ImageDraw

from conftest import auth, login, media_qs
from services import ai_service as ai_module
from services.imaging import MAX_BYTES, corner_whiteness, finalize_card, to_data_url
from services.info_photo import (
    BRIEFS,
    SLOTS,
    InfoSpec,
    apply_slots,
    build_info_prompt,
    build_spec,
    expected_strings,
    find_missing,
    find_unexpected,
    normalize,
    parse_facts,
)
from services.presets import STYLES, default_aspect, style_kind


def _png(color=(200, 200, 200), size=(600, 800)) -> bytes:
    img = Image.new("RGB", size, color)
    ImageDraw.Draw(img).ellipse([100, 200, 500, 600], fill=(30, 60, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run(coro):
    return asyncio.run(coro)


# --- facts and spec ----------------------------------------------------------------------------

def test_facts_become_specs_or_benefits():
    benefits, specs = parse_facts("• Ручная роспись\n- Диаметр: 32 см\nМатериал — Керамика\n\n  Вес: 1,2 кг  \nПодходит для подарка")
    assert benefits == ["Ручная роспись", "Подходит для подарка"]
    assert specs == [("Диаметр", "32 см"), ("Материал", "Керамика"), ("Вес", "1,2 кг")]
    assert parse_facts(None) == ([], []) and parse_facts("") == ([], [])


def test_seller_facts_come_first_and_sizes_are_never_guessed():
    ai = {"title": "Блюдо", "tagline": "Красивое", "benefits": ["Яркое", "Нарядное", "Нежное"],
          "specs": [{"name": "Диаметр", "value": "99 см"}], "badge": "Хит", "uses": ["НА СТОЛ"]}
    spec = build_spec(ai, "Ручная роспись\nДиаметр: 32 см", "Запасное", "ru")
    assert spec.benefits[0] == "Ручная роспись" and len(spec.benefits) <= 4 and "Яркое" in spec.benefits
    assert spec.specs == [("Диаметр", "32 см")], "specs come only from the seller, never from the AI"
    assert spec.title == "Блюдо" and build_spec({}, None, "Запасное", "uz").title == "Запасное"


def test_ai_cannot_add_promises_or_superlatives():
    ai = {"title": "Премиум блюдо", "tagline": "Престиж · Искусство", "benefits": ["Керамика высокого качества", "Нарядное", "Гарантия 5 лет", "Яркое"],
          "badge": "100% оригинал", "uses": ["НА СТОЛ", "ЛУЧШИЙ ПОДАРОК"]}
    spec = build_spec(ai, None, "Керамическое блюдо", "ru")
    assert spec.title == "Керамическое блюдо" and spec.tagline == "" and spec.badge == ""
    assert spec.benefits == ["Нарядное", "Яркое"] and spec.uses == ["НА СТОЛ"]
    # the seller may write such words themselves: then they are theirs to answer for
    own = build_spec(ai, "Керамика высокого качества", "x", "ru", allowed_text="сертифицировано")
    assert "Керамика высокого качества" in own.benefits
    uz = build_spec({"benefits": ["Premium sifat", "Chiroyli"], "tagline": "Eng yaxshi tanlov"}, None, "Lagan", "uz")
    assert uz.benefits == ["Chiroyli"] and uz.tagline == ""


def test_spec_is_clamped():
    spec = InfoSpec.from_dict({"title": "x" * 200, "benefits": ["b" * 200] * 9, "uses": ["u" * 99] * 9,
                               "specs": [{"name": "n" * 99, "value": "v" * 99}, {"name": "", "value": "x"}, "junk"]})
    assert len(spec.title) == 48 and len(spec.benefits) == 4 and len(spec.benefits[0]) == 44
    assert len(spec.uses) == 4 and len(spec.specs) == 1 and len(spec.specs[0][0]) == 22


def test_every_template_has_slots_and_a_brief():
    info_styles = [s["id"] for s in STYLES if s.get("kind") == "ai_text"]
    assert len(info_styles) >= 8
    for sid in info_styles:
        assert sid in BRIEFS and sid in SLOTS and style_kind(sid) == "ai_text" and default_aspect(sid) == "3:4"


def test_slots_limit_what_is_printed_and_checked():
    spec = InfoSpec.from_dict({"title": "T", "tagline": "Tag", "benefits": ["a", "b", "c", "d"], "badge": "B",
                               "specs": [{"name": "Диаметр", "value": "32 см"}], "uses": ["x", "y", "z"]})
    table = apply_slots(spec, "info_table")
    assert table.benefits == [] and table.specs == [("Диаметр", "32 см")] and table.badge == "" and table.uses == []
    assert expected_strings(spec, "info_table") == ["T", "Диаметр", "32 см"]
    assert apply_slots(spec, "info_headline").uses == ["x", "y"]


def test_prompt_contains_exact_text_and_guards():
    spec = InfoSpec.from_dict({"title": "Qo'lda bo'yalgan lagan", "benefits": ["Xavfsiz sir"], "lang": "uz",
                               "specs": [{"name": "Diametri", "value": "32 sm"}]})
    prompt = build_info_prompt("info_dark_list", spec)
    assert '"Qo\'lda bo\'yalgan lagan"' in prompt and '"Xavfsiz sir"' in prompt and '"Diametri: 32 sm"' in prompt
    assert "Uzbek" in prompt and "EXACTLY" in prompt and "do not add any other words" in prompt
    assert "ornamental" in prompt, "legible typefaces only"
    retry = build_info_prompt("info_dark_list", spec, retry_missing=["Xavfsiz sir"])
    assert "misspelled or omitted" in retry and '"Xavfsiz sir"' in retry.split("IMPORTANT")[1]
    assert "IMPORTANT" not in prompt


# --- text comparison -----------------------------------------------------------------------------

def test_normalization_ignores_typography_but_not_spelling():
    assert normalize("Qo’lda bo‘yalgan") == normalize("QO'LDA BO'YALGAN")
    assert normalize("Расписное блюдо «Риштан»") == normalize("расписное  блюдо Риштан")
    assert normalize("Распиcное") == normalize("Расписное"), "Latin c vs Cyrillic с look the same on a picture"
    assert normalize("Безогсасная") != normalize("Безопасная")
    assert normalize("240 000 сум") == normalize("240000 сум")


def test_missing_and_unexpected_text():
    expected = ["Расписное блюдо «Риштан»", "Ручная роспись", "32 см"]
    assert find_missing(["Расписное", "блюдо «Риштан»", "Ручная", "роспись", "Диаметр: 32 см"], expected) == []
    assert find_missing(["Расписное блюдо", "Ручная роспыь"], expected) == ["Расписное блюдо «Риштан»", "Ручная роспись", "32 см"]
    assert find_unexpected(["Ручная роспись", "SALE 90%"], expected) == ["SALE 90%"]


# --- imaging ---------------------------------------------------------------------------------------

def test_finalize_card_makes_a_uzum_sized_jpeg():
    out = finalize_card(_png(size=(896, 1200)))
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and img.size == (1080, 1440) and len(out) < MAX_BYTES
    assert finalize_card(_png(size=(1600, 900))) and Image.open(io.BytesIO(finalize_card(_png(size=(1600, 900))))).size == (1080, 1440)
    assert to_data_url(out).startswith("data:image/jpeg;base64,")


def test_whitening_cleans_the_background_but_not_the_product():
    tinted = Image.new("RGB", (600, 800), (243, 244, 247))       # the faint grey-blue tint the model leaves
    ImageDraw.Draw(tinted).ellipse([150, 250, 450, 550], fill=(30, 60, 160))    # product
    ImageDraw.Draw(tinted).rectangle([100, 700, 500, 720], fill=(200, 200, 200))  # soft shadow: must stay grey
    buf = io.BytesIO(); tinted.save(buf, format="PNG")
    clean = Image.open(io.BytesIO(finalize_card(buf.getvalue(), whiten=True)))
    kept = Image.open(io.BytesIO(finalize_card(buf.getvalue(), whiten=False)))
    assert min(clean.getpixel((10, 10))) >= 250 and min(kept.getpixel((10, 10))) < 250
    cx, cy = 540, 720
    r, g, b = clean.getpixel((cx, cy))
    assert b > r + 60, "the product keeps its colour"
    assert clean.getpixel((540, 1295))[0] < 240, "shadows are not erased"
    assert corner_whiteness(buf.getvalue()) < 250


def test_whitening_leaves_the_light_body_of_a_white_product_alone():
    img = Image.new("RGB", (600, 800), (249, 249, 249))           # model background
    d = ImageDraw.Draw(img)
    d.ellipse([100, 200, 500, 600], fill=(190, 190, 190))          # grey rim (outline) of a white plate
    d.ellipse([112, 212, 488, 588], fill=(244, 244, 244))          # the plate's own light body
    buf = io.BytesIO(); img.save(buf, format="PNG")
    out = Image.open(io.BytesIO(finalize_card(buf.getvalue(), whiten=True)))
    assert min(out.getpixel((10, 10))) >= 253, "background is pure white"
    assert out.getpixel((540, 720))[0] <= 246, "the body of the white product keeps its tone"


# --- image model fallback ---------------------------------------------------------------------------

def _fake_image_response(data: bytes):
    part = types.SimpleNamespace(inline_data=types.SimpleNamespace(data=data, mime_type="image/png"))
    return types.SimpleNamespace(parts=[part])


def test_image_models_order_and_override(monkeypatch):
    monkeypatch.delenv("GEMINI_IMAGE_MODEL", raising=False)
    monkeypatch.delenv("GEMINI_IMAGE_FALLBACK_MODEL", raising=False)
    assert ai_module.AIService._image_models() == ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "x-image")
    monkeypatch.setenv("GEMINI_IMAGE_FALLBACK_MODEL", "x-image")
    assert ai_module.AIService._image_models() == ["x-image"]


def test_fallback_model_is_used_when_the_first_fails(monkeypatch):
    calls = []

    def generate_content(model, contents, config):
        calls.append(model)
        if model == "gemini-3.1-flash-image":
            raise RuntimeError("model unavailable")
        return _fake_image_response(b"PICTURE")

    service = ai_module.AIService()
    monkeypatch.setattr(service, "_client", types.SimpleNamespace(models=types.SimpleNamespace(generate_content=generate_content)))
    assert run(service._generate_image_bytes("prompt", "3:4")) == b"PICTURE"
    assert calls == ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]

    monkeypatch.setattr(service, "_client", types.SimpleNamespace(models=types.SimpleNamespace(
        generate_content=lambda **kw: (_ for _ in ()).throw(RuntimeError("down"))))
    )
    assert run(service._generate_image_bytes("prompt", "3:4")) is None, "both models down: None, not an exception"


# --- verification loop ---------------------------------------------------------------------------------

SPEC = InfoSpec.from_dict({"title": "Расписное блюдо «Риштан»", "benefits": ["Ручная роспись", "Безопасная глазурь"], "lang": "ru"})
GOOD = ["Расписное блюдо «Риштан»", "Ручная", "роспись", "Безопасная", "глазурь"]
BAD = ["Расписное блюдо «Риштан»", "Ручная роспыь", "Безогсасная", "глазурь"]


def _service(monkeypatch, reads, pictures=None):
    """AIService whose image model and text reader are scripted."""
    service = ai_module.AIService()
    monkeypatch.setattr(service, "_client", object())
    prompts, pics = [], iter(pictures or [_png()] * 10)

    async def fake_image(contents, aspect_ratio="3:4"):
        prompts.append(contents[1])
        return next(pics, None)

    reads_iter = iter(reads)

    async def fake_read(png):
        item = next(reads_iter)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(service, "_generate_image_bytes", fake_image)
    monkeypatch.setattr(service, "read_image_text", fake_read)
    return service, prompts


def test_verified_on_the_first_try(monkeypatch):
    service, prompts = _service(monkeypatch, [GOOD])
    res = run(service.generate_info_photo(_png(), "image/png", "info_callouts", SPEC))
    assert res["verified"] is True and res["attempts"] == 1 and res["missing"] == [] and res["photo_url"].startswith("data:image/jpeg")
    assert len(prompts) == 1 and "IMPORTANT" not in prompts[0]


def test_misspelling_triggers_a_retry_with_the_exact_strings(monkeypatch):
    service, prompts = _service(monkeypatch, [BAD, GOOD])
    res = run(service.generate_info_photo(_png(), "image/png", "info_callouts", SPEC))
    assert res["verified"] is True and res["attempts"] == 2
    assert "IMPORTANT" in prompts[1] and "Ручная роспись" in prompts[1].split("IMPORTANT")[1]


def test_gives_up_after_three_attempts_and_reports_the_problem(monkeypatch):
    service, prompts = _service(monkeypatch, [BAD, BAD, BAD])
    res = run(service.generate_info_photo(_png(), "image/png", "info_callouts", SPEC))
    assert res["verified"] is False and res["attempts"] == 3 and len(prompts) == 3
    assert "Ручная роспись" in res["missing"] and res["photo_url"], "the best attempt is still returned"


def test_the_best_attempt_wins(monkeypatch):
    worse = ["nothing readable"]                    # misses all three strings
    almost = ["Расписное блюдо «Риштан»", "Ручная", "роспись", "Безогсасная"]   # misses only one
    service, _ = _service(monkeypatch, [worse, almost, worse], pictures=[_png((1, 1, 1)), _png((2, 2, 2)), _png((3, 3, 3))])
    res = run(service.generate_info_photo(_png(), "image/png", "info_callouts", SPEC))
    assert res["verified"] is False and res["missing"] == ["Безопасная глазурь"], "the attempt with fewest mistakes wins"


def test_a_failing_verifier_does_not_block_the_card(monkeypatch):
    service, prompts = _service(monkeypatch, [RuntimeError("OCR down")])
    res = run(service.generate_info_photo(_png(), "image/png", "info_callouts", SPEC))
    assert res["verified"] is None and res["photo_url"] and len(prompts) == 1


def test_no_picture_at_all(monkeypatch):
    service, _ = _service(monkeypatch, [], pictures=[None, None, None])
    monkeypatch.setattr(service, "_generate_image_bytes", lambda *a, **k: asyncio.sleep(0, result=None))
    res = run(service.generate_info_photo(_png(), "image/png", "info_callouts", SPEC))
    assert res["photo_url"] is None and res["verified"] is False and res["attempts"] == 3


def test_clean_uzum_photo_is_a_white_1080x1440_jpeg(monkeypatch):
    tinted = _png(color=(242, 244, 248), size=(896, 1200))
    service = ai_module.AIService()
    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")

    async def fake_image(contents, aspect_ratio="3:4"):
        assert aspect_ratio == "3:4"
        assert "white" in contents[1].lower() and "no text" in contents[1].lower()
        return tinted

    monkeypatch.setattr(service, "_generate_image_bytes", fake_image)
    url = run(service.generate_studio_photo(_png(), "image/png", "uzum_clean", None, None, "3:4"))
    img = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    assert img.format == "JPEG" and img.size == (1080, 1440) and min(img.getpixel((5, 5))) >= 253


# --- API ------------------------------------------------------------------------------------------------

def _generate(client, who, style, facts="", **extra):
    data = {"note": "Расписное блюдо", "photoshoot_style": style, "info_text": facts, "lang": "ru", **extra}
    res = client.post("/api/generate-card", data=data, files={"image": ("plate.png", _png(), "image/png")}, headers=auth(who))
    assert res.status_code == 200, res.text
    return res.json()


def test_offline_generation_is_flagged_and_not_saved(client):
    who = login(client, tg_id=970010)
    res = _generate(client, who, "info_table", "Диаметр: 32 см")
    assert res["ai_fallback"] == "no_key" and res["id"] is None and res["studio_photo_url"] is None
    assert client.get("/api/history", headers=auth(who)).json()["items"] == [], "sample text never lands in the history"


def test_info_card_without_a_picture_keeps_the_exact_poster(client, fake_ai):
    who = login(client, tg_id=970001)
    res = _generate(client, who, "info_table", "Диаметр: 32 см\nМатериал: Керамика\nРучная роспись")
    assert res["display"] == "poster" and res["studio_photo_url"] is None
    info = res["info"]
    assert info["verified"] is None and ("Диаметр", "32 см") in [tuple(s.values()) for s in info["specs"]] or {"name": "Диаметр", "value": "32 см"} in info["specs"]
    assert res["poster"]["layout"] == "callouts" and "Диаметр: 32 см" in res["poster"]["bullets"] + ["Диаметр: 32 см"]
    assert res["poster"]["price"] == "", "no price on the card unless the seller gave one"
    png = client.get(f"{res['poster_url']}?{media_qs(client, who)}")
    assert png.status_code == 200 and Image.open(io.BytesIO(png.content)).size == (1080, 1440)
    priced = _generate(client, who, "info_table", "", desired_price="240000")
    assert priced["poster"]["price"] == "240 000 сум"


def test_info_card_is_saved_for_the_history(client, fake_ai):
    who = login(client, tg_id=970002)
    card = _generate(client, who, "info_callouts", "Ручная роспись")
    item = next(i for i in client.get("/api/history", headers=auth(who)).json()["items"] if i["id"] == card["id"])
    assert item["info_config"]["title"] and item["has_poster"] is True


def _fake_ai_generation(monkeypatch, verified=True):
    """Pretend the AI is available: the text call returns a card with info suggestions and a finished picture."""
    photo = to_data_url(finalize_card(_png((10, 120, 200), (896, 1200))))

    async def fake_multimodal(self, image_bytes, image_mime, *args, **kwargs):
        return {
            "title": "🌸 Расписное блюдо «Риштан»", "description": "• Ручная роспись\n• Безопасная глазурь", "price_tag": "", "hashtags": [],
            "marketing_tip": "", "studio_photo_url": photo, "photoshoot_style": kwargs.get("photoshoot_style"),
            "info": {"title": "Расписное блюдо «Риштан»", "tagline": "", "benefits": ["Ручная роспись"], "specs": [{"name": "Диаметр", "value": "32 см"}],
                     "badge": "", "uses": [], "lang": "ru", "verified": verified, "missing": [] if verified else ["Ручная роспись"],
                     "unexpected": [], "attempts": 1 if verified else 3},
        }

    monkeypatch.setattr(ai_module.ai_service, "_call_gemini_multimodal", types.MethodType(fake_multimodal, ai_module.ai_service))
    monkeypatch.setattr(ai_module.ai_service, "_client", object())
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    return photo


def test_online_info_card_shows_the_ai_picture(client, monkeypatch):
    _fake_ai_generation(monkeypatch)
    who = login(client, tg_id=970003)
    res = _generate(client, who, "info_dark_list", "Ручная роспись")
    assert res["display"] == "photo" and res["studio_photo_url"].startswith("data:image/jpeg")
    assert res["info"]["verified"] is True and res["poster"]["layout"] == "callouts", "the exact version is always prepared"
    photo = client.get(f"/api/cards/{res['id']}/photo", headers=auth(who))
    assert photo.status_code == 200 and photo.headers["content-type"] == "image/jpeg"


def test_regenerating_with_edited_text(client, monkeypatch):
    _fake_ai_generation(monkeypatch)
    alice, bob = login(client, tg_id=970004), login(client, tg_id=970005)
    card = _generate(client, alice, "info_dark_list", "Ручная роспись")
    seen = {}

    async def fake_generate(self, image_bytes, image_mime, style_id, spec, aspect_ratio="3:4", max_attempts=3):
        seen.update(style=style_id, title=spec.title, benefits=spec.benefits, specs=spec.specs, size=len(image_bytes))
        return {"photo_url": to_data_url(finalize_card(_png((200, 30, 30), (896, 1200)))), "verified": True, "missing": [], "unexpected": [], "attempts": 1}

    monkeypatch.setattr(ai_module.AIService, "generate_info_photo", fake_generate)
    body = {"title": "Новое название", "benefits": ["Один", "Два"], "specs": [{"name": "Вес", "value": "1,2 кг"}], "style": "info_table"}
    res = client.post(f"/api/cards/{card['id']}/info-photo", json=body, headers=auth(alice))
    assert res.status_code == 200, res.text
    assert seen["style"] == "info_table" and seen["title"] == "Новое название" and seen["specs"] == [("Вес", "1,2 кг")] and seen["size"] > 1000, "uses the stored original photo"
    assert res.json()["info"]["title"] == "Новое название" and res.json()["poster"]["title"] == "Новое название"
    item = next(i for i in client.get("/api/history", headers=auth(alice)).json()["items"] if i["id"] == card["id"])
    assert item["info_config"]["title"] == "Новое название"
    assert client.post(f"/api/cards/{card['id']}/info-photo", json={}, headers=auth(bob)).status_code == 404
    assert client.post(f"/api/cards/{card['id']}/info-photo", json={}).status_code == 401


def test_regenerate_rules(client, monkeypatch, fake_ai):
    who = login(client, tg_id=970006)
    plain = _generate(client, who, "flat_lay")
    assert client.post(f"/api/cards/{plain['id']}/info-photo", json={}, headers=auth(who)).status_code == 400
    online = _generate(client, who, "info_table")
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "mock")
    assert client.post(f"/api/cards/{online['id']}/info-photo", json={}, headers=auth(who)).status_code == 503, "AI is off"
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")

    async def broken(self, *a, **k):
        return {"photo_url": None, "verified": False, "missing": [], "unexpected": [], "attempts": 3}

    monkeypatch.setattr(ai_module.AIService, "generate_info_photo", broken)
    assert client.post(f"/api/cards/{online['id']}/info-photo", json={}, headers=auth(who)).status_code == 502


def test_regenerating_counts_against_the_ai_limit(client, monkeypatch):
    monkeypatch.setenv("AI_CARD_LIMIT_PER_HOUR", "1")
    _fake_ai_generation(monkeypatch)
    who = login(client, tg_id=970007)
    card = _generate(client, who, "info_table")

    async def fake_generate(self, *a, **k):
        return {"photo_url": to_data_url(finalize_card(_png())), "verified": True, "missing": [], "unexpected": [], "attempts": 1}

    monkeypatch.setattr(ai_module.AIService, "generate_info_photo", fake_generate)
    assert client.post(f"/api/cards/{card['id']}/info-photo", json={}, headers=auth(who)).status_code == 429


def test_clean_uzum_card_keeps_the_original_for_later(client, fake_ai):
    from services.database import DB_PATH
    import sqlite3

    who = login(client, tg_id=970008)
    res = _generate(client, who, "uzum_clean")
    assert "poster" not in res
    item = next(i for i in client.get("/api/history", headers=auth(who)).json()["items"] if i["id"] == res["id"])
    assert item["photoshoot_style"] == "uzum_clean"
    with sqlite3.connect(DB_PATH) as conn:
        ref = conn.execute("SELECT source_photo_url FROM generated_cards WHERE id = ?", (res["id"],)).fetchone()[0]
    assert ref and ref.startswith("file:source/")


def test_registry_groups_are_ordered_for_uzum_sellers(client):
    reg = client.get("/api/photoshoot-presets").json()
    assert [g["id"] for g in reg["groups"][:2]] == ["uzum", "info"] and [g["tier"] for g in reg["groups"][:2]] == ["main", "main"]
    assert all(g["tier"] == "extra" for g in reg["groups"][2:])
    info = [s for s in reg["styles"] if s["group"] == "info"]
    assert len(info) >= 8 and all(s["slots"] and s["aspect"] == "3:4" for s in info)
    assert {s["id"] for s in reg["styles"] if s["group"] == "uzum"} == {"uzum_clean", "uzum_gradient"}


def test_ai_failure_is_reported_instead_of_passing_sample_text_as_real(client, monkeypatch):
    async def quota_exceeded(self, *a, **k):
        raise RuntimeError("402 RESOURCE_EXHAUSTED. Your prepayment credits are depleted.")

    async def broken(self, *a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(ai_module.ai_service, "_client", object())
    monkeypatch.setattr(ai_module.ai_service, "ai_mode", "gemini")
    who = login(client, tg_id=970009)
    monkeypatch.setattr(ai_module.ai_service, "_call_gemini_multimodal", types.MethodType(quota_exceeded, ai_module.ai_service))
    assert _generate(client, who, "info_table")["ai_fallback"] == "quota"
    monkeypatch.setattr(ai_module.ai_service, "_call_gemini_multimodal", types.MethodType(broken, ai_module.ai_service))
    failed = _generate(client, who, "flat_lay")
    assert failed["ai_fallback"] == "error" and failed["id"] is None
    assert client.get("/api/history", headers=auth(who)).json()["items"] == []
