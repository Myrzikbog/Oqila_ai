"""
presets.py — one registry for everything the photo studio can produce.

A *style* is what the AI draws. Styles of kind "ai_text" (information cards, posters, promos, infographics,
stories) carry text: their slots, limits and layout briefs live in services/info_photo.FORMATS and the AI
draws the text itself; the server never draws text on a marketing picture. "clean" styles are catalogue
photos without text, the rest are photo scenes.

The frontend reads this registry from GET /api/photoshoot-presets, so adding a style here is
all that is needed to offer it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.info_photo import FORMATS, format_fields, format_limits

# ---------------------------------------------------------------------------
# Output types shown as big cards in the Studio ("what do you want to get?")
# ---------------------------------------------------------------------------
GROUPS: List[Dict[str, Any]] = [
    # main: what sells on Uzum
    {"id": "uzum", "tier": "main", "icon": "shopping", "ru": "Фото для Uzum", "uz": "Uzum uchun surat",
     "hint_ru": "Чистое фото на белом фоне, 3:4", "hint_uz": "Oq fonda toza surat, 3:4"},
    {"id": "info", "tier": "main", "icon": "list", "ru": "Инфо-карточка", "uz": "Info-kartochka",
     "hint_ru": "Фото с размерами, преимуществами, иконками", "hint_uz": "O'lcham, afzallik va ikonkalar bilan surat"},
    # extra formats
    {"id": "photo", "tier": "extra", "icon": "camera", "ru": "Сцены и стили", "uz": "Sahna va uslublar",
     "hint_ru": "Красивая сцена вокруг товара", "hint_uz": "Mahsulot atrofida chiroyli sahna"},
    {"id": "poster", "tier": "extra", "icon": "layout", "ru": "Плакат", "uz": "Plakat",
     "hint_ru": "Товар, название, цена и контакты", "hint_uz": "Mahsulot, nom, narx va kontaktlar"},
    {"id": "promo", "tier": "extra", "icon": "percent", "ru": "Акция", "uz": "Aksiya",
     "hint_ru": "Скидка, новинка, ограниченный тираж", "hint_uz": "Chegirma, yangilik, cheklangan"},
    {"id": "story", "tier": "extra", "icon": "smartphone", "ru": "Сторис", "uz": "Storis",
     "hint_ru": "Вертикально, с кнопкой «Заказать»", "hint_uz": "Vertikal, «Buyurtma» tugmasi bilan"},
]

# ---------------------------------------------------------------------------
# Aspect ratios: the size of the finished JPEG and the ratio asked from the image model.
# The model draws 4:5 natively; set GEMINI_IMAGE_4_5=0 for a model without it and the 4:5 picture is cut from
# a 3:4 one instead (the text check always runs on the finished, cut picture).
# ---------------------------------------------------------------------------
ASPECTS: Dict[str, Dict[str, Any]] = {
    "1:1": {"size": (1080, 1080), "model": "1:1"},
    "4:5": {"size": (1080, 1350), "model": "4:5"},
    "3:4": {"size": (1080, 1440), "model": "3:4"},
    "9:16": {"size": (1080, 1920), "model": "9:16"},
}
DEFAULT_ASPECT = "1:1"


def model_aspect(aspect: str) -> str:
    """The aspect ratio to request from the image model for a finished picture of `aspect`."""
    import os

    if aspect == "4:5" and os.getenv("GEMINI_IMAGE_4_5", "1").strip().lower() in ("0", "false", "no"):
        return "3:4"
    return ASPECTS.get(aspect, ASPECTS[DEFAULT_ASPECT])["model"]


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
_SCENE_TAIL = " Keep the product from the reference photo exactly as it is (same shape, colour, pattern and details)."

STYLES: List[Dict[str, Any]] = [

    # ---- Uzum: clean catalogue photos ----------------------------------------
    {
        "id": "uzum_clean", "group": "uzum", "kind": "clean", "aspect": "3:4", "icon": "shopping", "featured": True,
        "preview": "/examples/uzum_clean.jpg",
        "ru": "Чистое фото", "uz": "Toza surat", "tag_ru": "Белый фон", "tag_uz": "Oq fon",
        "hint_ru": "Только товар на белом фоне, без лишних предметов, 3:4 (1080×1440)",
        "hint_uz": "Faqat mahsulot oq fonda, ortiqcha narsalarsiz, 3:4 (1080×1440)",
        "prompt": "Create a clean marketplace catalog photo of the product from the reference photo. Remove everything else from the scene (other objects, hands, table, clutter). Pure white seamless background (#FFFFFF), the product centered and filling about 80% of the frame, shown fully with nothing cropped, slight elevated front angle, soft even studio lighting, a subtle natural contact shadow under the product. No text, no logos, no watermarks, no props. Sharp focus, photorealistic.",
    },
    {
        "id": "uzum_gradient", "group": "uzum", "kind": "clean", "aspect": "3:4", "icon": "layers", "featured": True,
        "preview": "/examples/uzum_gradient.jpg",
        "ru": "Студия, светлый фон", "uz": "Studiya, och fon", "tag_ru": "Серый градиент", "tag_uz": "Kulrang gradient",
        "hint_ru": "Товар на светло-сером студийном фоне с мягкой тенью",
        "hint_uz": "Mahsulot och kulrang studiya fonida, yumshoq soya bilan",
        "prompt": "Create a premium marketplace studio photo of the product from the reference photo. Remove everything else from the scene. Soft light-grey seamless studio background with a gentle vertical gradient, the product centered and filling about 75% of the frame, shown fully, soft diffused studio lighting, a natural soft shadow on the floor. No text, no logos, no watermarks, no props. Sharp focus, photorealistic.",
    },

    # ---- information cards (the AI draws the text, the server verifies it) ----
    {
        "id": "info_white_specs", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "list", "featured": True,
        "preview": "/examples/info_white_specs.jpg",
        "ru": "Белый: размеры и характеристики", "uz": "Oq: o'lcham va tavsiflar", "tag_ru": "Как у брелоков", "tag_uz": "Brelok uslubida",
        "hint_ru": "Белый фон, заголовок, размерные линии и список характеристик", "hint_uz": "Oq fon, sarlavha, o'lcham chiziqlari va tavsiflar ro'yxati", "prompt": "",
    },
    {
        "id": "info_theme_benefits", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "sparkles", "featured": True,
        "preview": "/examples/info_theme_benefits.jpg",
        "ru": "Постер с иконками", "uz": "Ikonkali plakat", "tag_ru": "Яркий, тематический", "tag_uz": "Yorqin, mavzuli",
        "hint_ru": "Цветной фон под товар, большой заголовок, преимущества с иконками, плашка и ряд значков", "hint_uz": "Mahsulotga mos rangli fon, katta sarlavha, ikonkali afzalliklar, nishon va ikonkalar qatori", "prompt": "",
    },
    {
        "id": "info_headline", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "type", "featured": True,
        "preview": "/examples/info_headline.jpg",
        "ru": "Крупный заголовок", "uz": "Katta sarlavha", "tag_ru": "Фото + надпись", "tag_uz": "Surat + yozuv",
        "hint_ru": "Фото товара в жизни и огромный заголовок на нём", "hint_uz": "Hayotiy suratda mahsulot va ustida katta sarlavha", "prompt": "",
    },
    {
        "id": "info_collection", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "gift", "featured": True,
        "preview": "/examples/info_collection.jpg",
        "ru": "Набор / коллекция", "uz": "To'plam / kolleksiya", "tag_ru": "Для наборов", "tag_uz": "To'plamlar uchun",
        "hint_ru": "Эффектный фон, крупный заголовок, ряд иконок с подписями внизу", "hint_uz": "Ta'sirchan fon, katta sarlavha, pastda yozuvli ikonkalar qatori", "prompt": "",
    },
    {
        "id": "info_dark_list", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "moon", "featured": True,
        "preview": "/examples/info_dark_list.jpg",
        "ru": "Тёмный постер", "uz": "Qora plakat", "tag_ru": "Список с иконками", "tag_uz": "Ikonkali ro'yxat",
        "hint_ru": "Тёмный фон, заголовок, список преимуществ с иконками, характеристика и теги", "hint_uz": "Qora fon, sarlavha, ikonkali afzalliklar ro'yxati, tavsif va teglar", "prompt": "",
    },
    {
        "id": "info_dark_pills", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "crown", "featured": True,
        "preview": "/examples/info_dark_pills.jpg",
        "ru": "Тёмный премиум", "uz": "Qora premium", "tag_ru": "Плашки", "tag_uz": "Plashkalar",
        "hint_ru": "Тёмный атлас, товар по центру, преимущества в полупрозрачных плашках", "hint_uz": "Qora atlas, mahsulot o'rtada, afzalliklar shaffof plashkalarda", "prompt": "",
    },
    {
        "id": "info_callouts", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "list", "featured": False,
        "preview": "/examples/info_callouts.jpg",
        "ru": "Выноски", "uz": "Izohlar", "tag_ru": "Преимущества", "tag_uz": "Afzalliklar",
        "hint_ru": "Светлый фон, товар в центре, преимущества выносками", "hint_uz": "Och fon, mahsulot o'rtada, afzalliklar izoh sifatida", "prompt": "",
    },
    {
        "id": "info_table", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "columns", "featured": False,
        "preview": "/examples/info_table.jpg",
        "ru": "Таблица", "uz": "Jadval", "tag_ru": "Характеристики", "tag_uz": "Tavsiflar",
        "hint_ru": "Товар сверху, таблица характеристик под ним", "hint_uz": "Mahsulot tepada, ostida tavsiflar jadvali", "prompt": "",
    },

    # ---- photo scenes -----------------------------------------------------
    {
        "id": "minimal_studio", "group": "photo", "icon": "camera",
        "ru": "Студийный свет", "uz": "Studiya nuri", "tag_ru": "Каталог", "tag_uz": "Katalog", "featured": True,
        "hint_ru": "Студийный свет, нейтральный светлый подиум, мягкие тени",
        "hint_uz": "Studiya nuri, neytral yorug' podium, yumshoq soyalar",
        "prompt": "Professional commercial studio photoshoot of this item. Placed on an elegant clean podium, soft diffused studio lighting, minimalist neutral beige/white background, ultra sharp 8k product catalog photography.",
    },
    {
        "id": "uzbek_heritage", "group": "photo", "icon": "sparkles",
        "ru": "Восточный колорит", "uz": "Sharq ruhi", "tag_ru": "Икат/Атлас", "tag_uz": "Ikat/Atlas", "featured": True,
        "hint_ru": "Узбекский интерьер, резное дерево, ткань икат, тёплый свет",
        "hint_uz": "O'zbek interyeri, o'ymakor yog'och, ikat mato, iliq nur",
        "prompt": "Professional product photoshoot in an authentic Uzbek traditional interior. Beautiful carved wood details, subtle national silk ikat textures in background, warm ambient lighting, heritage craftsmanship aesthetic.",
    },
    {
        "id": "uzum_catalog", "group": "photo", "icon": "shopping",
        "ru": "Uzum (белый фон)", "uz": "Uzum (oq fon)", "tag_ru": "Маркетплейс", "tag_uz": "Marketpleys", "featured": True,
        "hint_ru": "Белоснежный фон, ровный свет, чёткие детали",
        "hint_uz": "Oppoq fon, bir tekis yorug'lik, aniq detallar",
        "prompt": "Clean e-commerce product catalog photo on pure white seamless background, soft balanced commercial lighting, subtle natural ground shadow, high commercial sharpness tailored for Uzum Market seller listing.",
    },
    {
        "id": "luxury_dark", "group": "photo", "icon": "crown",
        "ru": "Luxury тёмный", "uz": "Hashamatli qora", "tag_ru": "Премиум", "tag_uz": "Premium", "featured": True,
        "hint_ru": "Тёмный мрамор, драматичный свет, золотистые блики",
        "hint_uz": "Qora marmar, dramatik yorug'lik, tillarang jilo",
        "prompt": "Luxury editorial product photoshoot. Moody dark slate/obsidian background, warm dramatic spotlighting, polished dark marble surface, subtle gold reflections, premium high-end boutique aesthetic.",
    },
    {
        "id": "natural_light", "group": "photo", "icon": "sun",
        "ru": "Природный свет", "uz": "Tabiiy yorug'lik", "tag_ru": "Эко/Лайф", "tag_uz": "Eko/Layf", "featured": True,
        "hint_ru": "Утренний солнечный свет, натуральное дерево, зелень на фоне",
        "hint_uz": "Tonggi quyosh nuri, tabiiy yog'och, orqa fonda yashillik",
        "prompt": "Outdoor lifestyle product photography. Natural warm morning sunlight, organic wooden surface, gentle morning breeze, soft green botanical bokeh background, warm aesthetic depth of field.",
    },
    {
        "id": "flat_lay", "group": "photo", "icon": "layers",
        "ru": "Вид сверху", "uz": "Yuqoridan ko'rinish", "tag_ru": "Flat lay", "tag_uz": "Flat lay",
        "hint_ru": "Раскладка сверху на светлой ткани, аккуратные аксессуары вокруг",
        "hint_uz": "Yuqoridan, och mato ustida, atrofida chiroyli aksessuarlar",
        "prompt": "Top-down flat lay product photography on a soft light linen surface, the product centered, a few tasteful complementary props around it (dried flowers, a sprig of greenery), soft even daylight, editorial styling.",
    },
    {
        "id": "in_hands", "group": "photo", "icon": "hand",
        "ru": "В руках", "uz": "Qo'lda", "tag_ru": "Лайфстайл", "tag_uz": "Layfstayl",
        "hint_ru": "Товар в руках человека, живая естественная съёмка",
        "hint_uz": "Mahsulot qo'lda, tabiiy jonli suratga olish",
        "prompt": "Lifestyle photo of the product held gently in a person's hands (hands only, no face), warm natural window light, shallow depth of field, cozy authentic mood, soft neutral background.",
    },
    {
        "id": "gift_box", "group": "photo", "icon": "gift",
        "ru": "Подарок", "uz": "Sovg'a", "tag_ru": "Подарочный", "tag_uz": "Sovg'a",
        "hint_ru": "Подарочная упаковка, лента, праздничное настроение",
        "hint_uz": "Sovg'a qadog'i, lenta, bayram kayfiyati",
        "prompt": "Gift presentation: the product next to an elegant gift box with a satin ribbon, soft festive bokeh lights, warm pastel background, premium gifting aesthetic.",
    },
    {
        "id": "navruz", "group": "photo", "icon": "flower",
        "ru": "Навруз", "uz": "Navro'z", "tag_ru": "Праздник", "tag_uz": "Bayram",
        "hint_ru": "Весенний Навруз: сумаляк, тюльпаны, зелень, национальные узоры",
        "hint_uz": "Bahor Navro'zi: sumalak, lolalar, ko'katlar, milliy naqshlar",
        "prompt": "Navruz spring holiday scene: the product on a festive table with fresh tulips, green sprouts, a ceramic bowl of sumalak and subtle Uzbek ornament textiles, bright soft spring daylight, joyful warm atmosphere.",
    },
    {
        "id": "march8", "group": "photo", "icon": "heart",
        "ru": "8 Марта", "uz": "8-mart", "tag_ru": "Праздник", "tag_uz": "Bayram",
        "hint_ru": "Нежные цветы, пастельные тона, подарочное настроение",
        "hint_uz": "Nafis gullar, pastel ranglar, sovg'a kayfiyati",
        "prompt": "International Women's Day gift scene: the product surrounded by soft pastel tulips and mimosa, delicate ribbon, pastel pink and cream background, tender elegant mood, soft diffused light.",
    },
    {
        "id": "dastarkhan", "group": "photo", "icon": "utensils",
        "ru": "Дастархан", "uz": "Dasturxon", "tag_ru": "Для еды", "tag_uz": "Taomlar uchun",
        "hint_ru": "Накрытый дастархан, чай, сухофрукты, домашний уют",
        "hint_uz": "Yozilgan dasturxon, choy, quruq mevalar, uy qulayligi",
        "prompt": "Food product on a generously set Uzbek dastarkhan: green tea in a piala, dried fruits and nuts, patterned ceramic plates, warm homely light, appetizing close-up food photography.",
    },
    {
        "id": "on_model", "group": "photo", "icon": "user",
        "ru": "На модели", "uz": "Modelda", "tag_ru": "Для одежды", "tag_uz": "Kiyim uchun",
        "hint_ru": "Одежда или аксессуар на человеке, без показа лица",
        "hint_uz": "Kiyim yoki aksessuar odamda, yuzi ko'rsatilmaydi",
        "prompt": "Fashion lookbook photo: the garment or accessory worn by a model photographed from the neck down (face not shown), clean light studio backdrop, flattering soft light, natural pose, magazine quality.",
    },
    {
        "id": "collage_3", "group": "photo", "icon": "grid",
        "ru": "Коллаж 3 ракурса", "uz": "3 burchakli kollaj", "tag_ru": "Коллаж", "tag_uz": "Kollaj",
        "hint_ru": "Один товар с трёх сторон в аккуратной сетке",
        "hint_uz": "Bitta mahsulot uch tomondan, tartibli setkada",
        "prompt": "A tidy collage of three photos of the same product from three different angles (front, side and a close-up of the detail) in a clean grid with thin white gaps, consistent soft studio lighting, neutral background.",
    },
    {
        "id": "custom", "group": "photo", "icon": "sliders",
        "ru": "Своё описание", "uz": "O'z tavsifim", "tag_ru": "Свободный", "tag_uz": "Erkin",
        "hint_ru": "", "hint_uz": "", "prompt": "",
    },

    # ---- posters, promos, story: the AI draws the picture together with its text -------------
    {
        "id": "poster_showcase", "group": "poster", "kind": "ai_text", "aspect": "3:4", "icon": "layout",
        "ru": "Витрина", "uz": "Vitrina", "tag_ru": "Название сверху", "tag_uz": "Nom tepada",
        "hint_ru": "Крупный товар, название сверху, цена и контакты внизу",
        "hint_uz": "Yirik mahsulot, nom tepada, narx va kontakt pastda", "prompt": "",
    },
    {
        "id": "poster_magazine", "group": "poster", "kind": "ai_text", "aspect": "3:4", "icon": "columns",
        "ru": "Журнальный", "uz": "Jurnal", "tag_ru": "Список преимуществ", "tag_uz": "Afzalliklar ro'yxati",
        "hint_ru": "Товар справа, слева колонка с преимуществами и ценой",
        "hint_uz": "Mahsulot o'ngda, chapda afzalliklar va narx ustuni", "prompt": "",
    },
    {
        "id": "poster_minimal", "group": "poster", "kind": "ai_text", "aspect": "1:1", "icon": "minus",
        "ru": "Минимал", "uz": "Minimal", "tag_ru": "Много воздуха", "tag_uz": "Keng joy",
        "hint_ru": "Много воздуха, название и цена в нижней полосе",
        "hint_uz": "Keng joy, nom va narx pastki chiziqda", "prompt": "",
    },
    {
        "id": "market_callouts", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "list", "featured": False,
        "ru": "Инфографика с выносками", "uz": "Izohli infografika", "tag_ru": "Линии к деталям", "tag_uz": "Detallarga chiziqlar",
        "hint_ru": "Товар по центру, выноски с линиями к его деталям, цена",
        "hint_uz": "Mahsulot o'rtada, detallariga chiziqli izohlar, narx", "prompt": "",
    },
    {
        "id": "promo_sale", "group": "promo", "kind": "ai_text", "aspect": "1:1", "icon": "percent",
        "ru": "Скидка", "uz": "Chegirma", "tag_ru": "−% и срок", "tag_uz": "−% va muddat",
        "hint_ru": "Бейдж со скидкой, старая и новая цена, срок акции",
        "hint_uz": "Chegirma nishoni, eski va yangi narx, aksiya muddati", "prompt": "",
    },
    {
        "id": "promo_new", "group": "promo", "kind": "ai_text", "aspect": "1:1", "icon": "star",
        "ru": "Новинка", "uz": "Yangilik", "tag_ru": "NEW", "tag_uz": "NEW",
        "hint_ru": "Лента «Новинка», название и цена",
        "hint_uz": "«Yangilik» lentasi, nom va narx", "prompt": "",
    },
    {
        "id": "promo_limited", "group": "promo", "kind": "ai_text", "aspect": "4:5", "icon": "clock",
        "ru": "Ограниченный тираж", "uz": "Cheklangan nusxa", "tag_ru": "Осталось мало", "tag_uz": "Oz qoldi",
        "hint_ru": "Плашка «Осталось N штук», цена и срок внизу",
        "hint_uz": "«N dona qoldi» nishoni, narx va muddat pastda", "prompt": "",
    },
    {
        "id": "story_order", "group": "story", "kind": "ai_text", "aspect": "9:16", "icon": "smartphone",
        "ru": "Сторис «Заказать»", "uz": "Storis «Buyurtma»", "tag_ru": "9:16", "tag_uz": "9:16",
        "hint_ru": "Вертикальная сторис: название сверху, кнопка «Заказать» внизу",
        "hint_uz": "Vertikal storis: nom tepada, «Buyurtma» tugmasi pastda", "prompt": "",
    },
]

STYLES_BY_ID: Dict[str, Dict[str, Any]] = {s["id"]: s for s in STYLES}
DEFAULT_STYLE = "minimal_studio"


def get_style(style_id: Optional[str]) -> Dict[str, Any]:
    return STYLES_BY_ID.get(style_id or "", STYLES_BY_ID[DEFAULT_STYLE])


def style_kind(style_id: Optional[str]) -> str:
    """"clean" (catalogue photo without text), "ai_text" (the AI draws the picture with its text) or "scene"."""
    return get_style(style_id).get("kind") or "scene"


def default_aspect(style_id: Optional[str]) -> str:
    return get_style(style_id).get("aspect") or DEFAULT_ASPECT


def allowed_aspects(style_id: Optional[str]) -> List[str]:
    """Aspect ratios a style can be drawn in (formats with text list their own; photos take any)."""
    style = get_style(style_id)
    if style.get("kind") == "ai_text":
        return list(FORMATS[style["id"]]["aspects"])
    if style.get("kind") == "clean":
        return ["3:4"]
    return list(ASPECTS.keys())


def pick_aspect(style_id: Optional[str], wanted: Optional[str]) -> str:
    return wanted if wanted in allowed_aspects(style_id) else default_aspect(style_id)


def build_scene_prompt(style_id: Optional[str], extra: Optional[str] = None) -> str:
    """Prompt sent to the image model for a style (+ optional wishes typed by the user)."""
    style = get_style(style_id)
    prompt = style["prompt"]
    if prompt:
        prompt += _SCENE_TAIL
    if extra and extra.strip():
        prompt = f"{prompt} Additional wishes from the seller: {extra.strip()[:400]}".strip()
    return prompt


def public_registry() -> Dict[str, Any]:
    """JSON-friendly registry for the frontend (no server-only prompt text)."""
    styles = []
    for s in STYLES:
        item = {k: v for k, v in s.items() if k not in ("prompt", "layout")}
        item["kind"] = style_kind(s["id"])
        item["aspect"] = default_aspect(s["id"])
        item["aspects"] = allowed_aspects(s["id"])
        if item["kind"] == "ai_text":
            # what the text editor shows: the slots of this format with their counts and length limits
            item["fields"] = format_fields(s["id"])
            item["limits"] = format_limits(s["id"])
            item["max_blocks"] = FORMATS[s["id"]]["max_blocks"]
        styles.append(item)
    return {
        "groups": GROUPS,
        "styles": styles,
        "aspects": list(ASPECTS.keys()),
        "default_aspect": DEFAULT_ASPECT,
    }
