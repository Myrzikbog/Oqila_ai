"""Poster studio: style registry, poster renderer, poster/branding API."""
import io
import sqlite3

import pytest
from PIL import Image, ImageDraw

from conftest import auth, login, media_qs

pytestmark = pytest.mark.usefixtures("fake_ai")  # cards are only saved for real AI answers
from services import poster as poster_mod
from services.copy_utils import default_copy as poster_defaults
from services.imaging import normalize_logo, normalize_source
from services.poster import (
    PosterSpec,
    contrast_ratio,
    fit_text,
    keep_numbers_together,
    readable_on,
    render_poster,
    resolve_colors,
)
from services.presets import (
    ASPECTS,
    GROUPS,
    LAYOUTS,
    PALETTES,
    STYLES,
    STYLES_BY_ID,
    build_scene_prompt,
    default_aspect,
    needs_overlay,
    public_registry,
)


def _png(color=(200, 90, 60), size=(400, 300), mode="RGB") -> bytes:
    img = Image.new(mode, size, color)
    ImageDraw.Draw(img).ellipse([60, 60, size[0] - 60, size[1] - 60], fill=(250, 240, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate(client, who, style, **extra):
    data = {"note": "Расписная пиала", "desired_price": "240000", "photoshoot_style": style, "lang": "ru", **extra}
    res = client.post("/api/generate-card", data=data, files={"image": ("bowl.png", _png(), "image/png")}, headers=auth(who))
    assert res.status_code == 200, res.text
    return res.json()


# --- registry ----------------------------------------------------------------------------------

def test_registry_is_consistent():
    ids = [s["id"] for s in STYLES]
    assert len(ids) == len(set(ids)), "style ids must be unique"
    group_ids = {g["id"] for g in GROUPS}
    for style in STYLES:
        assert style["group"] in group_ids
        if style["layout"]:
            assert style["layout"] in LAYOUTS and LAYOUTS[style["layout"]]["group"] == style["group"]
        if style["id"] != "custom" and style.get("kind") != "ai_text":
            assert style["prompt"].strip(), style["id"]
            assert style["prompt"].isascii(), f"prompt of {style['id']} must be plain English"
        if style.get("kind") == "ai_text":
            from services.info_photo import BRIEFS, SLOTS
            assert style["id"] in BRIEFS and style["id"] in SLOTS, f"info style {style['id']} needs a brief and slots"
        for key in ("ru", "uz", "hint_ru", "hint_uz"):
            assert key in style
    for layout, info in LAYOUTS.items():
        assert any(s["layout"] == layout for s in STYLES), f"layout {layout} has no style"
        assert info["aspect"] in ASPECTS
    for group in GROUPS:
        assert any(s["group"] == group["id"] for s in STYLES)


def test_aspect_ratios_match_pixel_sizes():
    for name, info in ASPECTS.items():
        w, h = info["size"]
        a, b = (int(x) for x in name.split(":"))
        assert abs(w / h - a / b) < 0.002, name
        assert info["model"] in {"1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"}


def test_poster_prompts_reserve_space_for_text():
    prompt = build_scene_prompt("poster_showcase")
    assert "free of objects and text" in prompt and "exactly as it is" in prompt
    assert "Additional wishes" in build_scene_prompt("flat_lay", "with a blue ribbon")
    assert needs_overlay("poster_magazine") and not needs_overlay("flat_lay")
    assert default_aspect("story_order") == "9:16" and default_aspect("flat_lay") == "1:1"


def test_registry_endpoint_hides_prompts(client):
    res = client.get("/api/photoshoot-presets")
    assert res.status_code == 200
    data = res.json()
    assert "prompt" not in str(data["styles"]) and len(data["styles"]) == len(STYLES)
    assert set(data) >= {"groups", "styles", "layouts", "aspects", "palettes", "tones", "formats"}


# --- spec cleaning -----------------------------------------------------------------------------

def test_spec_clamps_and_validates():
    spec = PosterSpec.from_dict({
        "layout": "evil", "aspect": "7:3", "palette": "neon", "brand_color": "red", "title": "x" * 500,
        "bullets": ["a" * 200, "", "b", "c", "d", "e", "f"], "badge_text": "y" * 99, "price": "1\n2\r3",
    })
    assert spec.layout == "showcase" and spec.aspect == LAYOUTS["showcase"]["aspect"] and spec.palette == "brand"
    assert spec.brand_color == "" and len(spec.title) == 90 and len(spec.bullets) == 4
    assert len(spec.bullets[0]) == 60 and len(spec.badge_text) == 14 and spec.price == "1 2 3"


def test_custom_palette_needs_a_valid_colour():
    assert PosterSpec.from_dict({"palette": "custom"}).palette == "brand"
    assert PosterSpec.from_dict({"palette": "custom", "brand_color": "#7c3aed"}).palette == "custom"


# --- colours / accessibility -------------------------------------------------------------------

@pytest.mark.parametrize("name", list(PALETTES))
def test_builtin_palettes_are_readable(name):
    colors = resolve_colors(PosterSpec.from_dict({"palette": name}))
    assert contrast_ratio(colors.plate, colors.text) >= 4.5, "title text on the plate"
    assert contrast_ratio(colors.accent, colors.on_accent) >= 4.5, "text on price pills and badges"


@pytest.mark.parametrize("hex_color", ["#000000", "#ffffff", "#7c3aed", "#fde047", "#0f766e", "#ef4444", "#808080", "#10b981"])
def test_any_brand_colour_gives_readable_text(hex_color):
    colors = resolve_colors(PosterSpec.from_dict({"palette": "custom", "brand_color": hex_color}))
    assert contrast_ratio(colors.plate, colors.text) >= 4.5
    assert contrast_ratio(colors.accent, colors.on_accent) >= 4.5
    assert readable_on(colors.plate) == colors.text


# --- text fitting --------------------------------------------------------------------------------

def _draw():
    return ImageDraw.Draw(Image.new("RGB", (10, 10)))


def test_fit_text_never_exceeds_the_box():
    d = _draw()
    for text in ["Короткое", "Расписная пиала «Риштан» ручной работы с росписью", "Qo'lda bo'yalgan Rishton sopol lagan",
                 "Суперпупердлинноеназваниетоваракотороенепомещаетсянистрокуникогда " * 3]:
        f = fit_text(d, text, "xbold", 500, 200, 80, 24, 3)
        assert len(f.lines) <= 3
        assert f.width(d) <= 500 + 1, text
        assert f.height <= 200 or f.size == 24


def test_long_words_shrink_before_they_are_broken():
    d = _draw()
    f = fit_text(d, "Расписная пиала", "xbold", 330, 400, 90, 24, 5)
    assert set(" ".join(f.lines).split()) == {"Расписная", "пиала"}, f.lines  # whole words only
    assert f.size < 90, "the font shrank to make the longest word fit"


def test_phone_numbers_stay_together():
    assert keep_numbers_together("+998 90 123 45 67") == "+998 90 123 45 67"
    d = _draw()
    f = fit_text(d, keep_numbers_together("@oqila_shop +998 90 123 45 67"), "medium", 240, 200, 30, 20, 3)
    assert any("+998 90 123 45 67" in line for line in f.lines)


# --- rendering -----------------------------------------------------------------------------------

BASE = {"title": "Расписная пиала «Риштан» ручной работы", "price": "240 000 сум", "old_price": "300 000 сум",
        "bullets": ["Ручная роспись", "Безопасная глазурь", "Подарочная коробка"], "badge_text": "-20%",
        "deadline": "до 25 ноября", "contact": "@oqila_shop +998 90 123 45 67", "brand_name": "Oqila Home"}


@pytest.mark.parametrize("layout", list(LAYOUTS))
@pytest.mark.parametrize("lang", ["ru", "uz"])
def test_every_layout_renders_at_the_right_size(layout, lang):
    spec = PosterSpec.from_dict({**BASE, "layout": layout, "lang": lang})
    img = render_poster(spec, source=Image.open(io.BytesIO(_png())))
    assert img.size == ASPECTS[spec.aspect]["size"] and img.mode == "RGB"


@pytest.mark.parametrize("aspect", list(ASPECTS))
def test_any_aspect_works_with_any_layout(aspect):
    for layout in LAYOUTS:
        img = render_poster(PosterSpec.from_dict({**BASE, "layout": layout, "aspect": aspect}))
        assert img.size == ASPECTS[aspect]["size"]


def test_empty_and_extreme_input_does_not_crash():
    for layout in LAYOUTS:
        render_poster(PosterSpec.from_dict({"layout": layout}))
        render_poster(PosterSpec.from_dict({"layout": layout, "title": "ы" * 90, "price": "9" * 28, "contact": "z" * 48,
                                            "bullets": ["w" * 60] * 4, "brand_name": "B" * 32, "badge_text": "W" * 14}))


def test_ai_scene_and_source_photo_are_used_differently():
    spec = PosterSpec.from_dict({**BASE, "layout": "minimal"})
    scene = Image.new("RGB", (900, 900), (10, 200, 10))
    source = Image.open(io.BytesIO(_png((200, 20, 20))))
    with_scene = render_poster(spec, background=scene, source=source)
    only_source = render_poster(spec, source=source)
    plain = render_poster(spec)
    assert with_scene.getpixel((540, 200))[1] > 150, "AI scene is the background when present"
    assert only_source.tobytes() != plain.tobytes() and with_scene.tobytes() != only_source.tobytes()


def test_logo_transparency_is_kept():
    logo = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(logo).ellipse([20, 20, 180, 180], fill=(255, 0, 0, 255))
    spec = PosterSpec.from_dict({**BASE, "layout": "minimal", "palette": "light"})
    img = render_poster(spec, logo=logo)
    # the footer chip is white under the logo: its transparent corner must not turn black
    footer_corner = [img.getpixel((x, y)) for x in range(60, 150) for y in range(1080 - 54 - 80, 1080 - 54 - 20)]
    assert not any(p == (0, 0, 0) for p in footer_corner)


def test_logo_and_source_normalizers():
    assert normalize_logo(_png(mode="RGBA", size=(2000, 1000)))[:8] == b"\x89PNG\r\n\x1a\n"
    assert Image.open(io.BytesIO(normalize_logo(_png(size=(2000, 1000))))).width <= 512
    assert normalize_source(_png(size=(3000, 2000)))[:2] == b"\xff\xd8"
    for bad in (b"not an image", b"<svg onload=alert(1)/>", b""):
        with pytest.raises(ValueError):
            normalize_logo(bad)
        with pytest.raises(ValueError):
            normalize_source(bad)


def test_defaults_are_taken_from_the_card():
    card = {"title": "🌸 «Anor» — Milliy uslubdagi premium buyum", "price_tag": "💰 Narx: 380 000 so'm",
            "description": "🌸 Matn.\n\n✨ Afzalliklari:\n• Yuqori sifatli xomashyo\n• Cheklangan nusxa\n• Sovg'a qutisi\n\n📦 Yetkazib berish"}
    d = poster_defaults(card, 380000, "uz")
    assert d["title"].startswith("Anor") and "🌸" not in d["title"] and "«" not in d["title"]
    assert d["price"] == "380 000 so'm" and d["bullets"][:2] == ["Yuqori sifatli xomashyo", "Cheklangan nusxa"]
    # no explicit price: take it from the card's price tag
    assert poster_defaults(card, None, "uz")["price"].startswith("380 000")
    assert poster_defaults({"title": "T"}, 150000, "ru")["price"] == "150 000 сум"


def test_defaults_handle_price_ranges_and_quoted_titles():
    ranged = {"title": "«Анор» — Эксклюзивное авторское изделие", "price_tag": "💰 Цена: 380 000 – 420 000 сум"}
    d = poster_defaults(ranged, None, "ru")
    assert d["price"] == "от 380 000 сум", d["price"]
    assert d["title"] == "Анор — Эксклюзивное авторское изделие", d["title"]
    assert poster_defaults({"price_tag": "380 000 – 420 000 so'm"}, None, "uz")["price"] == "380 000 so'mdan"
    assert poster_defaults({"price_tag": "Цена: 95 000 сум"}, None, "ru")["price"] == "95 000 сум"
    assert poster_defaults({"price_tag": "по запросу"}, None, "ru")["price"] == ""
    # a normal title keeps its quotes
    assert poster_defaults({"title": "Пиала «Риштан»"}, None, "ru")["title"] == "Пиала «Риштан»"


def test_defaults_prefer_short_benefits():
    desc = "• " + "очень длинное преимущество " * 3 + "\n• Короткое раз\n• Короткое два\n• Короткое три\n• Короткое четыре"
    assert poster_defaults({"description": desc}, None, "ru")["bullets"] == ["Короткое раз", "Короткое два", "Короткое три"]


# --- API -----------------------------------------------------------------------------------------

def test_generate_poster_returns_config_and_a_renderable_poster(client):
    who = login(client, tg_id=960001)
    result = _generate(client, who, "poster_showcase")
    cfg = result["poster"]
    assert cfg["layout"] == "showcase" and cfg["aspect"] == "3:4" and cfg["price"] == "240 000 сум" and cfg["title"]
    assert result["studio_photo_url"] is None, "the raw scene is not shipped to the client"
    png = client.get(f"{result['poster_url']}?{media_qs(client, who)}")
    assert png.status_code == 200 and png.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(png.content)).size == (1080, 1440)


def test_aspect_override_and_unknown_style(client):
    who = login(client, tg_id=960002)
    result = _generate(client, who, "poster_minimal", aspect_ratio="9:16")
    assert result["poster"]["aspect"] == "9:16"
    plain = _generate(client, who, "does_not_exist")
    assert "poster" not in plain and plain["photoshoot_style"] == "minimal_studio"


def test_non_poster_styles_are_unchanged(client):
    who = login(client, tg_id=960003)
    result = _generate(client, who, "flat_lay")
    assert "poster" not in result and result["title"]


def test_editing_the_poster_is_free_and_saved(client):
    who = login(client, tg_id=960004)
    card_id = _generate(client, who, "poster_magazine")["id"]
    edited = {"layout": "sale", "aspect": "1:1", "palette": "dark", "title": "Новая цена!", "price": "199 000 сум",
              "old_price": "240 000 сум", "badge_text": "-17%", "bullets": [], "contact": "@shop", "lang": "ru"}
    res = client.post(f"/api/cards/{card_id}/poster", json=edited, headers=auth(who))
    assert res.status_code == 200 and Image.open(io.BytesIO(res.content)).size == (1080, 1080)
    item = next(i for i in client.get("/api/history", headers=auth(who)).json()["items"] if i["id"] == card_id)
    assert item["has_poster"] and item["poster_url"] and item["poster_config"]["title"] == "Новая цена!"
    again = client.get(f"/api/cards/{card_id}/poster.png?{media_qs(client, who)}")
    assert again.content == res.content, "the saved config renders the same poster"


def test_posters_are_private(client):
    alice, bob = login(client, tg_id=960005), login(client, tg_id=960006)
    card_id = _generate(client, alice, "poster_showcase")["id"]
    assert client.get(f"/api/cards/{card_id}/poster.png").status_code == 401
    assert client.get(f"/api/cards/{card_id}/poster.png", headers=auth(bob)).status_code == 404
    assert client.post(f"/api/cards/{card_id}/poster", json={"title": "x"}, headers=auth(bob)).status_code == 404
    assert client.post(f"/api/cards/{card_id}/poster", json={"title": "x"}).status_code == 401


def test_poster_render_is_rate_limited(client, monkeypatch):
    monkeypatch.setenv("POSTER_RENDER_LIMIT_PER_HOUR", "2")
    who = login(client, tg_id=960007)
    card_id = _generate(client, who, "poster_showcase")["id"]
    codes = [client.post(f"/api/cards/{card_id}/poster", json={"title": f"t{i}"}, headers=auth(who)).status_code for i in range(4)]
    assert codes == [200, 200, 429, 429]


def test_deleting_a_card_removes_the_stored_photos(client):
    from services.database import DB_PATH
    from services.media_storage import resolve_photo

    who = login(client, tg_id=960008)
    card_id = _generate(client, who, "poster_showcase")["id"]
    with sqlite3.connect(DB_PATH) as conn:
        ref = conn.execute("SELECT source_photo_url FROM generated_cards WHERE id = ?", (card_id,)).fetchone()[0]
    path = resolve_photo(ref)
    assert path and path.exists()
    assert client.delete(f"/api/history/{card_id}", headers=auth(who)).status_code == 200
    assert not path.exists()


# --- branding ------------------------------------------------------------------------------------

def test_brand_roundtrip_and_validation(client):
    who = login(client, tg_id=960009)
    assert client.get("/api/brand").status_code == 401
    assert client.get("/api/brand", headers=auth(who)).json()["has_logo"] is False
    bad = client.put("/api/brand", json={"brand_color": "teal"}, headers=auth(who))
    assert bad.status_code == 400
    ok = client.put("/api/brand", json={"brand_name": "  Oqila   Home ", "brand_color": "#7C3AED", "brand_contact": "@oqila_shop"}, headers=auth(who))
    assert ok.json() == {"brand_name": "Oqila Home", "brand_color": "#7c3aed", "brand_contact": "@oqila_shop", "has_logo": False}


def test_logo_upload_rules(client):
    who = login(client, tg_id=960010)
    assert client.post("/api/brand/logo", files={"logo": ("x.png", b"nope", "image/png")}, headers=auth(who)).status_code == 415
    assert client.post("/api/brand/logo", files={"logo": ("big.png", b"0" * (2 * 1024 * 1024 + 10), "image/png")}, headers=auth(who)).status_code == 413
    assert client.get("/api/brand/logo.png", headers=auth(who)).status_code == 404
    up = client.post("/api/brand/logo", files={"logo": ("l.png", _png(mode="RGBA"), "image/png")}, headers=auth(who))
    assert up.status_code == 200 and up.json()["has_logo"] is True
    assert client.get("/api/brand/logo.png").status_code == 401
    logo = client.get(f"/api/brand/logo.png?{media_qs(client, who)}")
    assert logo.status_code == 200 and logo.content[:4] == b"\x89PNG"
    assert client.delete("/api/brand/logo", headers=auth(who)).json()["has_logo"] is False
    assert "brand_logo" not in client.get("/api/profile", headers=auth(who)).json()


def test_new_posters_use_the_saved_branding(client):
    who = login(client, tg_id=960011)
    client.put("/api/brand", json={"brand_name": "Silk House", "brand_color": "#7c3aed", "brand_contact": "+998 90 111 22 33"}, headers=auth(who))
    client.post("/api/brand/logo", files={"logo": ("l.png", _png(mode="RGBA"), "image/png")}, headers=auth(who))
    cfg = _generate(client, who, "poster_showcase")["poster"]
    assert cfg["brand_name"] == "Silk House" and cfg["contact"] == "+998 90 111 22 33"
    assert cfg["palette"] == "custom" and cfg["brand_color"] == "#7c3aed" and cfg["show_logo"] is True
    png = client.get(f"/api/cards/{_generate(client, who, 'poster_minimal')['id']}/poster.png?{media_qs(client, who)}")
    assert png.status_code == 200


def test_poster_module_has_no_network_or_unsafe_imports():
    source = open(poster_mod.__file__, encoding="utf-8").read()
    for forbidden in ("requests", "httpx", "urllib", "subprocess", "eval(", "exec("):
        assert forbidden not in source
