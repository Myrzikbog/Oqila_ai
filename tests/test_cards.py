"""Pictures with text (one AI pipeline for cards, posters, promos, stories), clean Uzum photos, text verification.
No network: the AI is scripted."""
import asyncio
import base64
import io
import json
import os
import types
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from conftest import auth, login, media_qs
from services import ai_service as ai_module
from services.imaging import MAX_BYTES, corner_whiteness, finalize_card, to_data_url
from services.info_photo import (
    FORMATS,
    LIMITS,
    CopySpec,
    apply_slots,
    build_copy,
    build_edit_prompt,
    build_render_prompt,
    count_blocks,
    describe_color,
    escape_quotes,
    expected_strings,
    format_limits,
    parse_facts,
    parse_ocr,
    shorten_copy,
    tokenize,
    too_long_fields,
    verify_text,
)
from services.presets import ASPECTS, STYLES, allowed_aspects, default_aspect, model_aspect, pick_aspect, style_kind

SNAPSHOTS = Path(__file__).parent / "snapshots" / "render_prompts.json"
TEXT_STYLES = sorted(FORMATS)


def _png(color=(200, 200, 200), size=(600, 800)) -> bytes:
    img = Image.new("RGB", size, color)
    ImageDraw.Draw(img).ellipse([100, 200, 500, 600], fill=(30, 60, 160))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def run(coro):
    return asyncio.run(coro)


FULL = {
    "title": "Расписное блюдо «Риштан»", "subtitle": "Нарядный · Яркий", "bullets": ["Ручная роспись", "Безопасная глазурь", "Для плова", "В подарок"],
    "specs": [{"name": "Диаметр", "value": "32 см"}, {"name": "Материал", "value": "Керамика"}, {"name": "Вес", "value": "1,2 кг"}],
    "price": 380000, "old_price": 450000, "badge": "Ручная работа", "deadline": "до 31 декабря", "cta": "Заказать",
    "contact": "@oqila_shop", "brand_name": "Oqila Home", "uses": ["НА СТОЛ", "В ПОДАРОК"], "lang": "ru",
}
FULL_UZ = {
    "title": "Qo'lda bo'yalgan lagan", "subtitle": "Bayramona · Yorqin", "bullets": ["Qo'l mehnati", "Xavfsiz sir", "Osh uchun", "Sovg'aga"],
    "specs": [{"name": "Diametri", "value": "32 sm"}, {"name": "Materiali", "value": "Sopol"}],
    "price": 380000, "old_price": 450000, "badge": "Qo'l ishi", "deadline": "31-dekabrgacha", "cta": "Buyurtma berish",
    "contact": "@oqila_shop", "brand_name": "Oqila Home", "uses": ["DASTURXONGA"], "lang": "uz",
}


# --- facts and copy ------------------------------------------------------------------------------

def test_facts_become_specs_or_benefits():
    benefits, specs = parse_facts("• Ручная роспись\n- Диаметр: 32 см\nМатериал — Керамика\n\n  Вес: 1,2 кг  \nПодходит для подарка")
    assert benefits == ["Ручная роспись", "Подходит для подарка"]
    assert specs == [("Диаметр", "32 см"), ("Материал", "Керамика"), ("Вес", "1,2 кг")]
    assert parse_facts(None) == ([], []) and parse_facts("") == ([], [])


def test_seller_facts_come_first_and_sizes_are_never_guessed():
    ai = {"title": "Блюдо", "tagline": "Красивое", "benefits": ["Яркое", "Нарядное", "Нежное"],
          "specs": [{"name": "Диаметр", "value": "99 см"}], "badge": "Хит", "uses": ["НА СТОЛ"]}
    copy = build_copy(ai, "Ручная роспись\nДиаметр: 32 см", "Запасное", "ru")
    assert copy.bullets[0] == "Ручная роспись" and len(copy.bullets) <= 4 and "Яркое" in copy.bullets
    assert copy.specs == [("Диаметр", "32 см")], "specs come only from the seller, never from the AI"
    assert copy.title == "Блюдо" and copy.subtitle == "Красивое" and build_copy({}, None, "Запасное", "uz").title == "Запасное"
    assert copy.cta == "Заказать" and build_copy({}, None, "x", "uz").cta == "Buyurtma berish"


def test_ai_cannot_add_promises_or_superlatives():
    ai = {"title": "Премиум блюдо", "tagline": "Престиж · Искусство", "benefits": ["Керамика высокого качества", "Нарядное", "Гарантия 5 лет", "Яркое"],
          "badge": "100% оригинал", "uses": ["НА СТОЛ", "ЛУЧШИЙ ПОДАРОК"]}
    copy = build_copy(ai, None, "Керамическое блюдо", "ru")
    assert copy.title == "Керамическое блюдо" and copy.subtitle == "" and copy.badge == ""
    assert copy.bullets == ["Нарядное", "Яркое"] and copy.uses == ["НА СТОЛ"]
    # the seller may write such words themselves: then they are theirs to answer for
    own = build_copy(ai, "Высокое качество", "x", "ru", allowed_text="сертифицировано")
    assert "Высокое качество" in own.bullets
    uz = build_copy({"benefits": ["Premium sifat", "Chiroyli"], "tagline": "Eng yaxshi tanlov"}, None, "Lagan", "uz")
    assert uz.bullets == ["Chiroyli"] and uz.subtitle == ""


def test_the_price_comes_only_from_the_sellers_form():
    ai = {"title": "Блюдо", "price": "99 000 сум", "old_price": "999 000", "discount": "-90%", "benefits": ["Яркое"]}
    assert build_copy(ai, None, "x", "ru").price == "", "the AI's own price is ignored"
    priced = build_copy(ai, None, "x", "ru", price=380000, old_price=450000)
    assert (priced.price, priced.old_price, priced.discount) == ("380 000 сум", "450 000 сум", "−16%")
    assert build_copy(ai, None, "x", "uz", price=380000).price == "380 000 so'm"
    # whatever is typed into a price field is re-formatted from its digits
    typed = CopySpec.from_dict({"price": "380000,00 сум!!", "old_price": "0450 000", "lang": "ru"})
    assert typed.price == "380 000 сум" and typed.old_price == "450 000 сум"
    assert CopySpec.from_dict({"price": "дёшево"}).price == ""
    assert CopySpec.from_dict({"price": 100, "old_price": 90}).old_price == "", "an old price that is not higher is dropped"
    assert CopySpec.from_dict({"discount": "15"}).discount == "−15%" and CopySpec.from_dict({"discount": "скидка"}).discount == ""


def test_copy_is_clamped_and_accepts_old_field_names():
    copy = CopySpec.from_dict({"title": "x" * 200, "benefits": ["b" * 200, "c" * 200] * 4, "uses": ["u" * 99, "v" * 99] * 4,
                               "tagline": "t" * 99, "badge_text": "g" * 99,
                               "specs": [{"name": "n" * 99, "value": "v" * 99}, {"name": "", "value": "x"}, "junk"]})
    assert len(copy.title) == LIMITS["title"] == 32 and len(copy.bullets) == 2 and len(copy.bullets[0]) == LIMITS["bullet"] == 28
    assert len(copy.uses) == 2 and len(copy.specs) == 1 and len(copy.specs[0][0]) == LIMITS["spec_name"]
    assert len(copy.subtitle) == LIMITS["subtitle"] and len(copy.badge) == LIMITS["badge"] == 18 and LIMITS["cta"] == 18
    assert CopySpec.from_dict(None).title == ""
    # long text is cut at a word, not in the middle of one
    assert CopySpec.from_dict({"title": "Расписное керамическое блюдо ручной работы"}).title == "Расписное керамическое блюдо"


@pytest.mark.parametrize("style", TEXT_STYLES)
def test_every_format_is_registered_and_clamps_the_copy(style):
    fmt = FORMATS[style]
    assert style_kind(style) == "ai_text" and fmt["brief"] and fmt["slots"].get("title") == 1
    assert default_aspect(style) in fmt["aspects"] and all(a in ASPECTS for a in fmt["aspects"])
    long = {**FULL, "title": "Т" * 99, "bullets": ["п" * 99, "р" * 99, "с" * 99, "т" * 99], "subtitle": "п" * 99}
    cut = apply_slots(CopySpec.from_dict(long), style)
    lim = format_limits(style)
    assert len(cut.title) <= lim["title"] <= 32 and all(len(b) <= lim["bullet"] <= 28 for b in cut.bullets)
    assert len(cut.bullets) <= fmt["slots"].get("bullets", 0) and len(cut.specs) <= fmt["slots"].get("specs", 0)
    assert count_blocks(apply_slots(CopySpec.from_dict(FULL), style)) <= fmt["max_blocks"] <= 6
    if not fmt["slots"].get("price"):
        assert cut.price == "" and cut.old_price == "" and cut.discount == "", "a format without a price drops the price"
    else:
        assert cut.price == "380 000 сум"
    for slot in ("badge", "deadline", "cta", "contact", "brand_name", "subtitle"):
        if not fmt["slots"].get(slot):
            assert getattr(cut, slot) == ""


def test_story_has_few_blocks_and_only_its_own_aspect():
    story = apply_slots(CopySpec.from_dict(FULL), "story_order")
    assert count_blocks(story) <= 4 and FORMATS["story_order"]["max_blocks"] == 4
    assert allowed_aspects("story_order") == ["9:16"] and pick_aspect("story_order", "1:1") == "9:16"
    assert pick_aspect("promo_sale", "4:5") == "4:5" and pick_aspect("info_table", "9:16") == "3:4"
    assert allowed_aspects("uzum_clean") == ["3:4"]


def test_slots_limit_what_is_printed_and_checked():
    copy = CopySpec.from_dict(FULL)
    table = apply_slots(copy, "info_table")
    assert table.bullets == [] and table.specs[0] == ("Диаметр", "32 см") and table.badge == "" and table.uses == []
    assert expected_strings(copy, "info_table") == ["Расписное блюдо «Риштан»", "Диаметр", "32 см", "Материал", "Керамика", "Вес", "1,2 кг"]
    assert apply_slots(copy, "info_headline").uses == ["НА СТОЛ", "В ПОДАРОК"]
    sale = expected_strings(copy, "promo_sale")
    assert "380 000 сум" in sale and "450 000 сум" in sale and "−16%" in sale


def test_shortened_copy_keeps_the_facts():
    copy = CopySpec.from_dict(FULL)
    light = shorten_copy(copy, "info_theme_benefits")
    full = apply_slots(copy, "info_theme_benefits")
    assert light.title == full.title and light.subtitle == "" and len(light.bullets) == len(full.bullets) - 1
    assert shorten_copy(copy, "promo_sale").price == "380 000 сум"
    assert too_long_fields({"title": "x" * 40, "bullets": ["ok", "y" * 40]}, "info_callouts") == ["title", "bullets.1"]


# --- prompts ----------------------------------------------------------------------------------------

def _all_prompts() -> dict:
    out = {}
    for style in TEXT_STYLES:
        for lang, data in (("ru", FULL), ("uz", FULL_UZ)):
            aspect = default_aspect(style)
            out[f"{style}/{lang}/{aspect}"] = build_render_prompt(CopySpec.from_dict(data), style, aspect, {"brand_color": "#0f766e", "has_logo": True})
    return out


def test_render_prompts_match_the_snapshots():
    """A prompt change is a product change: review the diff, then run with UPDATE_SNAPSHOTS=1."""
    current = _all_prompts()
    if os.getenv("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOTS.parent.mkdir(exist_ok=True)
        SNAPSHOTS.write_text(json.dumps(current, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    saved = json.loads(SNAPSHOTS.read_text(encoding="utf-8"))
    assert sorted(saved) == sorted(current)
    for key in current:
        assert current[key] == saved[key], f"prompt for {key} changed"


@pytest.mark.parametrize("style", TEXT_STYLES)
def test_prompt_lists_every_string_with_role_and_guards(style):
    copy = CopySpec.from_dict(FULL_UZ)
    prompt = build_render_prompt(copy, style, default_aspect(style))
    for i, value in enumerate([v for _, v in __import__("services.info_photo", fromlist=["text_items"]).text_items(apply_slots(copy, style))], 1):
        assert f'Text block {i} (' in prompt and f'"{value}"' in prompt
    assert "Uzbek, Latin script" in prompt and "do not transliterate to Cyrillic" in prompt and "apostrophe" in prompt
    assert "write digits exactly as given; thousands separated by a space" in prompt
    assert "do not add any other text, numbers, prices, logos or watermarks" in prompt
    assert "at least 6%" in prompt and "ornamental" in prompt and "EXACTLY" in prompt
    assert "BRAND" not in prompt and "LOGO" not in prompt
    assert "Russian, Cyrillic script only" in build_render_prompt(CopySpec.from_dict(FULL), style, default_aspect(style))


def test_prompt_layout_briefs_orientation_and_brand():
    copy = CopySpec.from_dict(FULL)
    assert "upper third" in build_render_prompt(copy, "poster_showcase", "3:4")
    sale = build_render_prompt(copy, "promo_sale", "1:1")
    assert "square 1:1" in sale and "corner" in sale and "crossed out" in sale and '"−16%"' in sale
    story = build_render_prompt(copy, "story_order", "9:16")
    assert "tall vertical 9:16" in story and "upper 20%" in story and "lower 25%" in story and "safe zone" in story
    assert "leader line" in build_render_prompt(copy, "market_callouts", "3:4")
    assert "vertical 4:5" in build_render_prompt(copy, "promo_limited", "4:5")
    branded = build_render_prompt(copy, "poster_minimal", "1:1", {"brand_color": "#7c3aed", "has_logo": True})
    assert "violet (#7c3aed)" in branded and "second reference image" in branded and "do not redraw" in branded
    assert describe_color("#0f766e") == "deep teal" and describe_color("#ffffff") == "white" and describe_color("oops") == ""


def test_quotes_inside_seller_text_are_escaped():
    assert escape_quotes('Пиала "Риштан" и "Гиждуван"') == "Пиала «Риштан» и «Гиждуван»"
    copy = CopySpec.from_dict({"title": 'Пиала "Риштан"', "bullets": ['Цвет "индиго"'], "lang": "ru"})
    prompt = build_render_prompt(copy, "info_callouts", "3:4")
    assert '"Пиала «Риштан»"' in prompt and '"Цвет «индиго»"' in prompt
    assert all(line.count('"') == 2 for line in prompt.splitlines() if line.startswith("Text block"))
    assert expected_strings(copy, "info_callouts")[0] == "Пиала «Риштан»", "the check expects what the prompt asked for"
    edit = build_edit_prompt([{"expected": 'Пиала "Риштан"', "found": "Пиала Риштон"}])
    assert 'replace text "Пиала Риштон" with exactly "Пиала «Риштан»"' in edit and "keep the layout" in edit
    assert 'write exactly "X"' in build_edit_prompt([{"expected": "X", "found": ""}])
    assert 'remove the text "SALE 90%"' in build_edit_prompt([{"expected": "", "found": "SALE 90%"}])


# --- line-by-line text check ---------------------------------------------------------------------

def _check(blocks, expected):
    return verify_text(blocks, expected)


def test_good_picture_passes_with_wrapped_lines_and_table_cells():
    expected = ["Расписное блюдо «Риштан»", "Ручная роспись", "Диаметр", "32 см", "380 000 сум"]
    blocks = [["РАСПИСНОЕ БЛЮДО", "«РИШТАН»"], ["Ручная роспись"], ["Диаметр: 32 см"], ["380000 сум"]]
    res = _check(blocks, expected)
    assert res == {"verified": True, "problems": [], "unexpected": []}
    assert tokenize("Распиcное") == tokenize("Расписное"), "Latin c and Cyrillic с look the same on a picture"
    assert tokenize("Нарядный — Яркий") == tokenize("нарядный яркий"), "case, dashes and spacing are soft"


def test_missing_apostrophe_is_a_mistake():
    assert tokenize("Qo’lda bo‘yalgan") == tokenize("QO'LDA BO'YALGAN"), "apostrophe styles are equivalent"
    res = _check([["Qolda boyalgan lagan"]], ["Qo'lda bo'yalgan lagan"])
    assert res["verified"] is False and res["problems"] == [{"expected": "Qo'lda bo'yalgan lagan", "found": "Qolda boyalgan lagan"}]
    assert _check([["Qoʻlda boʻyalgan lagan"]], ["Qo'lda bo'yalgan lagan"])["verified"] is True


def test_a_swapped_price_digit_is_a_mistake():
    res = _check([["Блюдо"], ["308 000 сум"]], ["Блюдо", "380 000 сум"])
    assert res["verified"] is False and res["problems"][0] == {"expected": "380 000 сум", "found": "308 000 сум"}
    assert _check([["1 380 000 сум"]], ["380 000 сум"])["verified"] is False, "a longer number is another number"
    assert _check([["380 000 so'm"]], ["380 000 сум"])["verified"] is False, "the currency word is strict"
    assert _check([["15"]], ["−15%"])["verified"] is False, "the percent sign is strict"
    assert _check([["1.2 кг"]], ["12 кг"])["verified"] is False and _check([["1,2 кг"]], ["1,2 кг"])["verified"] is True


def test_an_extra_price_is_a_mistake_and_extra_words_are_reported():
    res = _check([["Блюдо"], ["380 000 сум"], ["Скидка 50%"], ["Лучший выбор"]], ["Блюдо", "380 000 сум"])
    assert res["verified"] is False and {"expected": "", "found": "Скидка 50%"} in res["problems"]
    assert res["unexpected"] == ["Лучший выбор"], "extra words are listed, extra numbers are errors"
    # the same approved number drawn twice (a dimension line and a table) is fine
    assert _check([["32 см"], ["Диаметр: 32 см"]], ["Диаметр", "32 см"])["verified"] is True


def test_a_string_spread_over_two_blocks_is_not_found():
    expected = ["Ручная роспись"]
    assert _check([["Ручная", "роспись"]], expected)["verified"] is True, "two lines of one block: a wrapped title"
    res = _check([["Ручная"], ["роспись"]], expected)
    assert res["verified"] is False and res["problems"][0]["expected"] == "Ручная роспись"


def test_a_number_inside_another_number_is_not_a_match():
    for line in ("320 см", "132 см", "32 000 сум", "Арт. 3210"):
        res = _check([[line]], ["32 см"])
        assert res["verified"] is False and res["problems"][0]["expected"] == "32 см", line
    assert _check([["Диаметр 32 см"]], ["32 см"])["verified"] is True
    assert _check([["32 мм"]], ["32 см"])["verified"] is False


def test_ocr_answer_shapes():
    assert parse_ocr({"blocks": [{"lines": ["a", " b "]}, {"lines": []}, ["c"]]}) == [["a", "b"], ["c"]]
    assert parse_ocr({"lines": ["a", "b"]}) == [["a"], ["b"]], "no grouping: every line is its own block"
    assert parse_ocr(["a", {"text": "b"}]) == [["a"], ["b"]] and parse_ocr("junk") == []


# --- imaging ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("aspect,size", [("1:1", (1080, 1080)), ("3:4", (1080, 1440)), ("4:5", (1080, 1350)), ("9:16", (1080, 1920))])
def test_finalize_card_follows_the_aspect(aspect, size):
    out = finalize_card(_png(size=(900, 1200)), size=ASPECTS[aspect]["size"])
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and img.size == size and len(out) < MAX_BYTES


def test_4_5_is_drawn_natively_or_cut_from_3_4(monkeypatch):
    monkeypatch.delenv("GEMINI_IMAGE_4_5", raising=False)
    assert model_aspect("4:5") == "4:5" and model_aspect("9:16") == "9:16"
    monkeypatch.setenv("GEMINI_IMAGE_4_5", "0")
    assert model_aspect("4:5") == "3:4"


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


def test_pictures_with_text_never_use_the_fallback_model(monkeypatch):
    calls = []

    def generate_content(model, contents, config):
        calls.append(model)
        raise RuntimeError("model unavailable")

    service = ai_module.AIService()
    monkeypatch.setattr(service, "_client", types.SimpleNamespace(models=types.SimpleNamespace(generate_content=generate_content)))
    assert run(service._generate_image_bytes("prompt", "3:4", with_fallback=False)) is None
    assert calls == ["gemini-3.1-flash-image"], "the older model misspells text: an honest error is better"


# --- render_card: generate, check, edit, regenerate ------------------------------------------------

COPY = CopySpec.from_dict({"title": "Расписное блюдо «Риштан»", "subtitle": "Нарядный · Яркий", "bullets": ["Ручная роспись", "Безопасная глазурь", "Для плова"], "lang": "ru"})
STYLE = "info_dark_pills"
GOOD = [["Расписное блюдо «Риштан»"], ["Нарядный · Яркий"], ["Ручная", "роспись"], ["Безопасная глазурь"], ["Для плова"]]
BAD2 = [["Расписное блюдо «Риштан»"], ["Нарядный · Яркий"], ["Ручная роспыь"], ["Безогсасная глазурь"], ["Для плова"]]
BAD1 = [["Расписное блюдо «Риштан»"], ["Нарядный · Яркий"], ["Ручная роспись"], ["Безогсасная глазурь"], ["Для плова"]]
LIGHT_GOOD = [["Расписное блюдо «Риштан»"], ["Ручная роспись"], ["Безопасная глазурь"]]


def scripted(monkeypatch, reads, pictures=None, service=None):
    """An AIService whose image model and text reader follow a script. Returns (service, log of image calls)."""
    service = service or ai_module.AIService()
    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")
    log, pics, reads_iter = [], iter(pictures if pictures is not None else [_png((i, i, i)) for i in range(1, 9)]), iter(reads)

    async def fake_image(contents, aspect_ratio="3:4", with_fallback=True):
        log.append({"prompt": contents[-1], "refs": len(contents) - 1, "aspect": aspect_ratio, "fallback": with_fallback})
        return next(pics, None)

    async def fake_read(image):
        item = next(reads_iter)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(service, "_generate_image_bytes", fake_image)
    monkeypatch.setattr(service, "read_image_text", fake_read)
    return service, log


def _render(service, copy=COPY, style=STYLE, aspect="3:4", **kw):
    return run(service.render_card(copy, style, aspect, _png(), **kw))


def test_render_succeeds_on_the_first_try(monkeypatch):
    service, log = scripted(monkeypatch, [GOOD])
    res = _render(service, brand={"brand_color": "#7c3aed"}, logo=_png())
    assert res["verification"]["verified"] is True and res["image_calls"] == 1 and len(log) == 1
    assert Image.open(io.BytesIO(res["photo"])).size == (1080, 1440) and res["copy"]["title"] == COPY.title
    assert log[0]["refs"] == 2 and "LOGO" in log[0]["prompt"] and "violet" in log[0]["prompt"], "photo + logo as references"
    assert log[0]["fallback"] is False


def test_render_is_fixed_by_an_edit(monkeypatch):
    service, log = scripted(monkeypatch, [BAD1, GOOD])
    res = _render(service)
    assert res["verification"]["verified"] is True and res["image_calls"] == 2
    assert log[1]["refs"] == 1 and log[1]["prompt"].startswith("Edit this image"), "the edit works on the previous picture"
    assert 'replace text "Безогсасная глазурь" with exactly "Безопасная глазурь"' in log[1]["prompt"]


def test_two_edits_when_the_first_one_helps(monkeypatch):
    service, log = scripted(monkeypatch, [BAD2, BAD1, GOOD])
    res = _render(service)
    assert res["verification"]["verified"] is True and res["image_calls"] == 3
    assert [l["prompt"].startswith("Edit this image") for l in log] == [False, True, True]


def test_render_is_regenerated_with_a_lighter_copy_when_the_edit_does_not_help(monkeypatch):
    service, log = scripted(monkeypatch, [BAD1, BAD1, LIGHT_GOOD])
    res = _render(service)
    assert res["verification"]["verified"] is True and res["image_calls"] == 3
    assert log[2]["prompt"].startswith("Design a finished") and log[2]["refs"] == 1, "a full regeneration, not an edit"
    assert "Нарядный · Яркий" not in log[2]["prompt"] and "Для плова" not in log[2]["prompt"]
    assert res["copy"]["subtitle"] == "" and res["copy"]["bullets"] == ["Ручная роспись", "Безопасная глазурь"], "the copy that is really on the picture"


def test_render_gives_up_after_three_image_calls_and_reports_the_problems(monkeypatch):
    pictures = [_png((1, 1, 1)), _png((2, 2, 2)), _png((3, 3, 3))]
    service, log = scripted(monkeypatch, [BAD2, BAD1, BAD1], pictures=pictures)
    res = _render(service)
    assert res["image_calls"] == 3 and len(log) == 3
    assert res["verification"]["verified"] is False
    assert res["verification"]["problems"] == [{"expected": "Безопасная глазурь", "found": "Безогсасная глазурь"}], "the best attempt wins"
    assert res["photo"], "the best picture is returned; the server never draws the text itself"


def test_render_with_a_failing_reader_retries_the_reader_once(monkeypatch):
    service, log = scripted(monkeypatch, [RuntimeError("OCR down"), GOOD])
    res = _render(service)
    assert res["verification"]["verified"] is True and res["image_calls"] == 1, "one reader retry, no new picture"
    service, log = scripted(monkeypatch, [RuntimeError("down"), RuntimeError("down")])
    res = _render(service)
    assert res["verification"] == {"verified": None, "problems": [], "unexpected": []} and res["photo"] and res["image_calls"] == 1


def test_render_without_a_picture(monkeypatch):
    service, log = scripted(monkeypatch, [], pictures=[])
    res = _render(service)
    assert res["photo"] is None and res["image_calls"] == 1 and res["verification"]["verified"] is None


def test_a_lost_edit_does_not_lose_the_first_picture(monkeypatch):
    service, log = scripted(monkeypatch, [BAD1, GOOD], pictures=[_png((1, 1, 1)), None, _png((3, 3, 3))])
    res = _render(service)
    assert res["photo"] and res["image_calls"] == 3 and res["verification"]["verified"] is True


@pytest.mark.parametrize("aspect,size", [("1:1", (1080, 1080)), ("4:5", (1080, 1350)), ("9:16", (1080, 1920))])
def test_render_size_follows_the_aspect_and_the_cut_picture_is_what_gets_checked(monkeypatch, aspect, size):
    service, log = scripted(monkeypatch, [])
    seen = []

    async def reader(image):
        seen.append(Image.open(io.BytesIO(image)).size)
        return GOOD

    monkeypatch.setattr(service, "read_image_text", reader)
    res = run(service.render_card(COPY, "promo_new" if aspect != "9:16" else "story_order", aspect, _png()))
    assert Image.open(io.BytesIO(res["photo"])).size == size and seen == [size] and log[0]["aspect"] == aspect


def test_fix_text_is_one_edit(monkeypatch):
    service, log = scripted(monkeypatch, [GOOD])
    res = run(service.fix_card_text(_png(), [{"expected": "Ручная роспись", "found": "Ручная роспыь"}], COPY, STYLE, "3:4"))
    assert res["verification"]["verified"] is True and res["image_calls"] == 1 and log[0]["prompt"].startswith("Edit this image")


def test_clean_uzum_photo_is_a_white_1080x1440_jpeg(monkeypatch):
    tinted = _png(color=(242, 244, 248), size=(896, 1200))
    service = ai_module.AIService()
    monkeypatch.setattr(service, "_client", object())
    monkeypatch.setattr(service, "ai_mode", "gemini")

    async def fake_image(contents, aspect_ratio="3:4", with_fallback=True):
        assert aspect_ratio == "3:4"
        assert "white" in contents[1].lower() and "no text" in contents[1].lower()
        return tinted

    monkeypatch.setattr(service, "_generate_image_bytes", fake_image)
    url = run(service.generate_studio_photo(_png(), "image/png", "uzum_clean", None, None, "3:4"))
    img = Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))
    assert img.format == "JPEG" and img.size == (1080, 1440) and min(img.getpixel((5, 5))) >= 253


