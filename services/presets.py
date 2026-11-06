"""
presets.py — one registry for everything the photo studio can produce.

A *style* is what the AI draws (a scene around the product). Styles of the poster, promo,
marketplace and story groups also name a *layout*: the AI is told to leave calm space for it and
the server then draws the text itself (services/poster.py), so prices, numbers and Uzbek letters
are always exact.

The frontend reads this registry from GET /api/photoshoot-presets, so adding a style here is
all that is needed to offer it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.info_photo import SLOTS as INFO_SLOTS

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
     "hint_ru": "Точный текст, правка без ИИ", "hint_uz": "Aniq matn, AIsiz tahrirlash"},
    {"id": "promo", "tier": "extra", "icon": "percent", "ru": "Акция", "uz": "Aksiya",
     "hint_ru": "Скидка, новинка, ограниченный тираж", "hint_uz": "Chegirma, yangilik, cheklangan"},
    {"id": "story", "tier": "extra", "icon": "smartphone", "ru": "Сторис", "uz": "Storis",
     "hint_ru": "Вертикально, с кнопкой «Заказать»", "hint_uz": "Vertikal, «Buyurtma» tugmasi bilan"},
]

# ---------------------------------------------------------------------------
# Aspect ratios. The image model supports 1:1, 2:3, 3:2, 3:4, 4:3, 9:16, 16:9, 21:9;
# 4:5 (Instagram) is made from a 3:4 image by the renderer.
# ---------------------------------------------------------------------------
ASPECTS: Dict[str, Dict[str, Any]] = {
    "1:1": {"size": (1080, 1080), "model": "1:1"},
    "4:5": {"size": (1080, 1350), "model": "3:4"},
    "3:4": {"size": (1080, 1440), "model": "3:4"},
    "9:16": {"size": (1080, 1920), "model": "9:16"},
}
DEFAULT_ASPECT = "1:1"

# ---------------------------------------------------------------------------
# Colour schemes for the text plates and badges
# ---------------------------------------------------------------------------
PALETTES: Dict[str, Dict[str, Any]] = {
    "brand": {"ru": "Бирюзовая", "uz": "Moviy-yashil", "plate": "#0f766e", "text": "#ffffff", "accent": "#fde68a", "swatch": "#0f766e"},
    "dark": {"ru": "Тёмная", "uz": "Qora", "plate": "#111827", "text": "#ffffff", "accent": "#fbbf24", "swatch": "#111827"},
    "light": {"ru": "Светлая", "uz": "Och", "plate": "#ffffff", "text": "#111827", "accent": "#be123c", "swatch": "#ffffff"},
    "warm": {"ru": "Тёплая", "uz": "Iliq", "plate": "#9a3412", "text": "#fff7ed", "accent": "#fed7aa", "swatch": "#9a3412"},
}
DEFAULT_PALETTE = "brand"

# ---------------------------------------------------------------------------
# Layouts (drawn by services/poster.py)
# `space` tells the AI where to keep the frame calm for text: top | left | bottom | none
# ---------------------------------------------------------------------------
LAYOUTS: Dict[str, Dict[str, Any]] = {
    "showcase": {"group": "poster", "ru": "Витрина", "uz": "Vitrina", "space": "top", "aspect": "3:4"},
    "magazine": {"group": "poster", "ru": "Журнальный", "uz": "Jurnal", "space": "left", "aspect": "3:4"},
    "minimal": {"group": "poster", "ru": "Минимал", "uz": "Minimal", "space": "bottom", "aspect": "1:1"},
    "sale": {"group": "promo", "ru": "Скидка", "uz": "Chegirma", "space": "top", "aspect": "1:1"},
    "new_arrival": {"group": "promo", "ru": "Новинка", "uz": "Yangilik", "space": "bottom", "aspect": "1:1"},
    "limited": {"group": "promo", "ru": "Ограниченный тираж", "uz": "Cheklangan nusxa", "space": "bottom", "aspect": "4:5"},
    "callouts": {"group": "poster", "ru": "Выноски", "uz": "Izohlar", "space": "none", "aspect": "3:4"},
    "story": {"group": "story", "ru": "Сторис", "uz": "Storis", "space": "top", "aspect": "9:16"},
}

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
_SCENE_TAIL = " Keep the product from the reference photo exactly as it is (same shape, colour, pattern and details)."

STYLES: List[Dict[str, Any]] = [

    # ---- Uzum: clean catalogue photos ----------------------------------------
    {
        "id": "uzum_clean", "group": "uzum", "kind": "clean", "aspect": "3:4", "icon": "shopping", "layout": None, "featured": True,
        "preview": "/examples/uzum_clean.jpg",
        "ru": "Чистое фото", "uz": "Toza surat", "tag_ru": "Белый фон", "tag_uz": "Oq fon",
        "hint_ru": "Только товар на белом фоне, без лишних предметов, 3:4 (1080×1440)",
        "hint_uz": "Faqat mahsulot oq fonda, ortiqcha narsalarsiz, 3:4 (1080×1440)",
        "prompt": "Create a clean marketplace catalog photo of the product from the reference photo. Remove everything else from the scene (other objects, hands, table, clutter). Pure white seamless background (#FFFFFF), the product centered and filling about 80% of the frame, shown fully with nothing cropped, slight elevated front angle, soft even studio lighting, a subtle natural contact shadow under the product. No text, no logos, no watermarks, no props. Sharp focus, photorealistic.",
    },
    {
        "id": "uzum_gradient", "group": "uzum", "kind": "clean", "aspect": "3:4", "icon": "layers", "layout": None, "featured": True,
        "preview": "/examples/uzum_gradient.jpg",
        "ru": "Студия, светлый фон", "uz": "Studiya, och fon", "tag_ru": "Серый градиент", "tag_uz": "Kulrang gradient",
        "hint_ru": "Товар на светло-сером студийном фоне с мягкой тенью",
        "hint_uz": "Mahsulot och kulrang studiya fonida, yumshoq soya bilan",
        "prompt": "Create a premium marketplace studio photo of the product from the reference photo. Remove everything else from the scene. Soft light-grey seamless studio background with a gentle vertical gradient, the product centered and filling about 75% of the frame, shown fully, soft diffused studio lighting, a natural soft shadow on the floor. No text, no logos, no watermarks, no props. Sharp focus, photorealistic.",
    },

    # ---- information cards (the AI draws the text, the server verifies it) ----
    {
        "id": "info_white_specs", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "list", "layout": None, "featured": True,
        "preview": "/examples/info_white_specs.jpg", "slots": INFO_SLOTS["info_white_specs"],
        "ru": "Белый: размеры и характеристики", "uz": "Oq: o'lcham va tavsiflar", "tag_ru": "Как у брелоков", "tag_uz": "Brelok uslubida",
        "hint_ru": "Белый фон, заголовок, размерные линии и список характеристик", "hint_uz": "Oq fon, sarlavha, o'lcham chiziqlari va tavsiflar ro'yxati", "prompt": "",
    },
    {
        "id": "info_theme_benefits", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "sparkles", "layout": None, "featured": True,
        "preview": "/examples/info_theme_benefits.jpg", "slots": INFO_SLOTS["info_theme_benefits"],
        "ru": "Постер с иконками", "uz": "Ikonkali plakat", "tag_ru": "Яркий, тематический", "tag_uz": "Yorqin, mavzuli",
        "hint_ru": "Цветной фон под товар, большой заголовок, преимущества с иконками, плашка и ряд значков", "hint_uz": "Mahsulotga mos rangli fon, katta sarlavha, ikonkali afzalliklar, nishon va ikonkalar qatori", "prompt": "",
    },
    {
        "id": "info_headline", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "type", "layout": None, "featured": True,
        "preview": "/examples/info_headline.jpg", "slots": INFO_SLOTS["info_headline"],
        "ru": "Крупный заголовок", "uz": "Katta sarlavha", "tag_ru": "Фото + надпись", "tag_uz": "Surat + yozuv",
        "hint_ru": "Фото товара в жизни и огромный заголовок на нём", "hint_uz": "Hayotiy suratda mahsulot va ustida katta sarlavha", "prompt": "",
    },
    {
        "id": "info_collection", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "gift", "layout": None, "featured": True,
        "preview": "/examples/info_collection.jpg", "slots": INFO_SLOTS["info_collection"],
        "ru": "Набор / коллекция", "uz": "To'plam / kolleksiya", "tag_ru": "Для наборов", "tag_uz": "To'plamlar uchun",
        "hint_ru": "Эффектный фон, крупный заголовок, ряд иконок с подписями внизу", "hint_uz": "Ta'sirchan fon, katta sarlavha, pastda yozuvli ikonkalar qatori", "prompt": "",
    },
    {
        "id": "info_dark_list", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "moon", "layout": None, "featured": True,
        "preview": "/examples/info_dark_list.jpg", "slots": INFO_SLOTS["info_dark_list"],
        "ru": "Тёмный постер", "uz": "Qora plakat", "tag_ru": "Список с иконками", "tag_uz": "Ikonkali ro'yxat",
        "hint_ru": "Тёмный фон, заголовок, список преимуществ с иконками, характеристика и теги", "hint_uz": "Qora fon, sarlavha, ikonkali afzalliklar ro'yxati, tavsif va teglar", "prompt": "",
    },
    {
        "id": "info_dark_pills", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "crown", "layout": None, "featured": True,
        "preview": "/examples/info_dark_pills.jpg", "slots": INFO_SLOTS["info_dark_pills"],
        "ru": "Тёмный премиум", "uz": "Qora premium", "tag_ru": "Плашки", "tag_uz": "Plashkalar",
        "hint_ru": "Тёмный атлас, товар по центру, преимущества в полупрозрачных плашках", "hint_uz": "Qora atlas, mahsulot o'rtada, afzalliklar shaffof plashkalarda", "prompt": "",
    },
    {
        "id": "info_callouts", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "list", "layout": None, "featured": False,
        "preview": "/examples/info_callouts.jpg", "slots": INFO_SLOTS["info_callouts"],
        "ru": "Выноски", "uz": "Izohlar", "tag_ru": "Преимущества", "tag_uz": "Afzalliklar",
        "hint_ru": "Светлый фон, товар в центре, преимущества выносками", "hint_uz": "Och fon, mahsulot o'rtada, afzalliklar izoh sifatida", "prompt": "",
    },
    {
        "id": "info_table", "group": "info", "kind": "ai_text", "aspect": "3:4", "icon": "columns", "layout": None, "featured": False,
        "preview": "/examples/info_table.jpg", "slots": INFO_SLOTS["info_table"],
        "ru": "Таблица", "uz": "Jadval", "tag_ru": "Характеристики", "tag_uz": "Tavsiflar",
        "hint_ru": "Товар сверху, таблица характеристик под ним", "hint_uz": "Mahsulot tepada, ostida tavsiflar jadvali", "prompt": "",
    },

    # ---- photo scenes -----------------------------------------------------
    {
        "id": "minimal_studio", "group": "photo", "icon": "camera", "layout": None,
        "ru": "Студийный свет", "uz": "Studiya nuri", "tag_ru": "Каталог", "tag_uz": "Katalog", "featured": True,
        "hint_ru": "Студийный свет, нейтральный светлый подиум, мягкие тени",
        "hint_uz": "Studiya nuri, neytral yorug' podium, yumshoq soyalar",
        "prompt": "Professional commercial studio photoshoot of this item. Placed on an elegant clean podium, soft diffused studio lighting, minimalist neutral beige/white background, ultra sharp 8k product catalog photography.",
    },
    {
        "id": "uzbek_heritage", "group": "photo", "icon": "sparkles", "layout": None,
        "ru": "Восточный колорит", "uz": "Sharq ruhi", "tag_ru": "Икат/Атлас", "tag_uz": "Ikat/Atlas", "featured": True,
        "hint_ru": "Узбекский интерьер, резное дерево, ткань икат, тёплый свет",
        "hint_uz": "O'zbek interyeri, o'ymakor yog'och, ikat mato, iliq nur",
        "prompt": "Professional product photoshoot in an authentic Uzbek traditional interior. Beautiful carved wood details, subtle national silk ikat textures in background, warm ambient lighting, heritage craftsmanship aesthetic.",
    },
    {
        "id": "uzum_catalog", "group": "photo", "icon": "shopping", "layout": None,
        "ru": "Uzum (белый фон)", "uz": "Uzum (oq fon)", "tag_ru": "Маркетплейс", "tag_uz": "Marketpleys", "featured": True,
        "hint_ru": "Белоснежный фон, ровный свет, чёткие детали",
        "hint_uz": "Oppoq fon, bir tekis yorug'lik, aniq detallar",
        "prompt": "Clean e-commerce product catalog photo on pure white seamless background, soft balanced commercial lighting, subtle natural ground shadow, high commercial sharpness tailored for Uzum Market seller listing.",
    },
    {
        "id": "luxury_dark", "group": "photo", "icon": "crown", "layout": None,
        "ru": "Luxury тёмный", "uz": "Hashamatli qora", "tag_ru": "Премиум", "tag_uz": "Premium", "featured": True,
        "hint_ru": "Тёмный мрамор, драматичный свет, золотистые блики",
        "hint_uz": "Qora marmar, dramatik yorug'lik, tillarang jilo",
        "prompt": "Luxury editorial product photoshoot. Moody dark slate/obsidian background, warm dramatic spotlighting, polished dark marble surface, subtle gold reflections, premium high-end boutique aesthetic.",
    },
    {
        "id": "natural_light", "group": "photo", "icon": "sun", "layout": None,
        "ru": "Природный свет", "uz": "Tabiiy yorug'lik", "tag_ru": "Эко/Лайф", "tag_uz": "Eko/Layf", "featured": True,
        "hint_ru": "Утренний солнечный свет, натуральное дерево, зелень на фоне",
        "hint_uz": "Tonggi quyosh nuri, tabiiy yog'och, orqa fonda yashillik",
        "prompt": "Outdoor lifestyle product photography. Natural warm morning sunlight, organic wooden surface, gentle morning breeze, soft green botanical bokeh background, warm aesthetic depth of field.",
    },
    {
        "id": "flat_lay", "group": "photo", "icon": "layers", "layout": None,
        "ru": "Вид сверху", "uz": "Yuqoridan ko'rinish", "tag_ru": "Flat lay", "tag_uz": "Flat lay",
        "hint_ru": "Раскладка сверху на светлой ткани, аккуратные аксессуары вокруг",
        "hint_uz": "Yuqoridan, och mato ustida, atrofida chiroyli aksessuarlar",
        "prompt": "Top-down flat lay product photography on a soft light linen surface, the product centered, a few tasteful complementary props around it (dried flowers, a sprig of greenery), soft even daylight, editorial styling.",
    },
    {
        "id": "in_hands", "group": "photo", "icon": "hand", "layout": None,
        "ru": "В руках", "uz": "Qo'lda", "tag_ru": "Лайфстайл", "tag_uz": "Layfstayl",
        "hint_ru": "Товар в руках человека, живая естественная съёмка",
        "hint_uz": "Mahsulot qo'lda, tabiiy jonli suratga olish",
        "prompt": "Lifestyle photo of the product held gently in a person's hands (hands only, no face), warm natural window light, shallow depth of field, cozy authentic mood, soft neutral background.",
    },
    {
        "id": "gift_box", "group": "photo", "icon": "gift", "layout": None,
        "ru": "Подарок", "uz": "Sovg'a", "tag_ru": "Подарочный", "tag_uz": "Sovg'a",
        "hint_ru": "Подарочная упаковка, лента, праздничное настроение",
        "hint_uz": "Sovg'a qadog'i, lenta, bayram kayfiyati",
        "prompt": "Gift presentation: the product next to an elegant gift box with a satin ribbon, soft festive bokeh lights, warm pastel background, premium gifting aesthetic.",
    },
    {
        "id": "navruz", "group": "photo", "icon": "flower", "layout": None,
        "ru": "Навруз", "uz": "Navro'z", "tag_ru": "Праздник", "tag_uz": "Bayram",
        "hint_ru": "Весенний Навруз: сумаляк, тюльпаны, зелень, национальные узоры",
        "hint_uz": "Bahor Navro'zi: sumalak, lolalar, ko'katlar, milliy naqshlar",
        "prompt": "Navruz spring holiday scene: the product on a festive table with fresh tulips, green sprouts, a ceramic bowl of sumalak and subtle Uzbek ornament textiles, bright soft spring daylight, joyful warm atmosphere.",
    },
    {
        "id": "march8", "group": "photo", "icon": "heart", "layout": None,
        "ru": "8 Марта", "uz": "8-mart", "tag_ru": "Праздник", "tag_uz": "Bayram",
        "hint_ru": "Нежные цветы, пастельные тона, подарочное настроение",
        "hint_uz": "Nafis gullar, pastel ranglar, sovg'a kayfiyati",
        "prompt": "International Women's Day gift scene: the product surrounded by soft pastel tulips and mimosa, delicate ribbon, pastel pink and cream background, tender elegant mood, soft diffused light.",
    },
    {
        "id": "dastarkhan", "group": "photo", "icon": "utensils", "layout": None,
        "ru": "Дастархан", "uz": "Dasturxon", "tag_ru": "Для еды", "tag_uz": "Taomlar uchun",
        "hint_ru": "Накрытый дастархан, чай, сухофрукты, домашний уют",
        "hint_uz": "Yozilgan dasturxon, choy, quruq mevalar, uy qulayligi",
        "prompt": "Food product on a generously set Uzbek dastarkhan: green tea in a piala, dried fruits and nuts, patterned ceramic plates, warm homely light, appetizing close-up food photography.",
    },
    {
        "id": "on_model", "group": "photo", "icon": "user", "layout": None,
        "ru": "На модели", "uz": "Modelda", "tag_ru": "Для одежды", "tag_uz": "Kiyim uchun",
        "hint_ru": "Одежда или аксессуар на человеке, без показа лица",
        "hint_uz": "Kiyim yoki aksessuar odamda, yuzi ko'rsatilmaydi",
        "prompt": "Fashion lookbook photo: the garment or accessory worn by a model photographed from the neck down (face not shown), clean light studio backdrop, flattering soft light, natural pose, magazine quality.",
    },
    {
        "id": "collage_3", "group": "photo", "icon": "grid", "layout": None,
        "ru": "Коллаж 3 ракурса", "uz": "3 burchakli kollaj", "tag_ru": "Коллаж", "tag_uz": "Kollaj",
        "hint_ru": "Один товар с трёх сторон в аккуратной сетке",
        "hint_uz": "Bitta mahsulot uch tomondan, tartibli setkada",
        "prompt": "A tidy collage of three photos of the same product from three different angles (front, side and a close-up of the detail) in a clean grid with thin white gaps, consistent soft studio lighting, neutral background.",
    },
    {
        "id": "custom", "group": "photo", "icon": "sliders", "layout": None,
        "ru": "Своё описание", "uz": "O'z tavsifim", "tag_ru": "Свободный", "tag_uz": "Erkin",
        "hint_ru": "", "hint_uz": "", "prompt": "",
    },

    # ---- poster (info + product) -------------------------------------------
    {
        "id": "poster_showcase", "group": "poster", "icon": "layout", "layout": "showcase",
        "ru": "Витрина", "uz": "Vitrina", "tag_ru": "Название сверху", "tag_uz": "Nom tepada",
        "hint_ru": "Крупный товар, название сверху, цена и контакты внизу",
        "hint_uz": "Yirik mahsulot, nom tepada, narx va kontakt pastda",
        "prompt": "Elegant advertising background for a product poster. The product is large, centered in the lower two thirds of the frame, beautifully lit; the top third of the frame is calm and softly blurred, free of objects and text.",
    },
    {
        "id": "poster_magazine", "group": "poster", "icon": "columns", "layout": "magazine",
        "ru": "Журнальный", "uz": "Jurnal", "tag_ru": "Список преимуществ", "tag_uz": "Afzalliklar ro'yxati",
        "hint_ru": "Товар справа, слева колонка с преимуществами и ценой",
        "hint_uz": "Mahsulot o'ngda, chapda afzalliklar va narx ustuni",
        "prompt": "Editorial magazine-style advertising background. The product is placed on the right half of the frame, beautifully lit; the left 40% of the frame is calm, softly blurred and free of objects and text.",
    },
    {
        "id": "poster_minimal", "group": "poster", "icon": "minus", "layout": "minimal",
        "ru": "Минимал", "uz": "Minimal", "tag_ru": "Много воздуха", "tag_uz": "Keng joy",
        "hint_ru": "Много воздуха, подпись и цена в нижней полосе",
        "hint_uz": "Keng joy, imzo va narx pastki chiziqda",
        "prompt": "Minimalist premium advertising background. The product is centered in the upper two thirds of the frame on a clean surface with generous negative space; the bottom fifth of the frame is calm, plain and free of objects and text.",
    },

    # ---- promo -----------------------------------------------------------
    {
        "id": "promo_sale", "group": "promo", "icon": "percent", "layout": "sale",
        "ru": "Скидка", "uz": "Chegirma", "tag_ru": "−% и срок", "tag_uz": "−% va muddat",
        "hint_ru": "Бейдж со скидкой, старая и новая цена, срок акции",
        "hint_uz": "Chegirma nishoni, eski va yangi narx, aksiya muddati",
        "prompt": "Energetic sales promotion background. The product is centered in the lower two thirds of the frame, vivid and bright; the top third is calm and uncluttered for a headline.",
    },
    {
        "id": "promo_new", "group": "promo", "icon": "star", "layout": "new_arrival",
        "ru": "Новинка", "uz": "Yangilik", "tag_ru": "NEW", "tag_uz": "NEW",
        "hint_ru": "Лента «Новинка», название и цена",
        "hint_uz": "«Yangilik» lentasi, nom va narx",
        "prompt": "Fresh new-arrival advertising background. The product is centered in the upper two thirds of the frame with soft spotlight; the bottom fifth is calm and uncluttered.",
    },
    {
        "id": "promo_limited", "group": "promo", "icon": "clock", "layout": "limited",
        "ru": "Ограниченный тираж", "uz": "Cheklangan nusxa", "tag_ru": "Эксклюзив", "tag_uz": "Eksklyuziv",
        "hint_ru": "Эксклюзивно: «Осталось N штук», цена внизу",
        "hint_uz": "Eksklyuziv: «N dona qoldi», narx pastda",
        "prompt": "Exclusive limited-edition advertising background in a luxurious mood. The product is centered in the upper two thirds of the frame with dramatic soft lighting; the bottom fifth is calm and uncluttered.",
    },

    # ---- marketplace infographic -------------------------------------------
    {
        "id": "market_callouts", "group": "poster", "icon": "list", "layout": "callouts",
        "ru": "Выноски (точный текст)", "uz": "Izohlar (aniq matn)", "tag_ru": "Без ИИ", "tag_uz": "AIsiz",
        "hint_ru": "Товар по центру, преимущества выносками слева и справа",
        "hint_uz": "Mahsulot o'rtada, afzalliklar chap va o'ngda izoh sifatida",
        "prompt": "Clean e-commerce infographic background: the product centered and large on a soft light neutral gradient background with plenty of calm space on both the left and right sides, soft natural shadow, high sharpness.",
    },

    # ---- story ------------------------------------------------------------
    {
        "id": "story_order", "group": "story", "icon": "smartphone", "layout": "story",
        "ru": "Сторис «Заказать»", "uz": "Storis «Buyurtma»", "tag_ru": "9:16", "tag_uz": "9:16",
        "hint_ru": "Вертикальная сторис: название сверху, кнопка «Заказать» внизу",
        "hint_uz": "Vertikal storis: nom tepada, «Buyurtma» tugmasi pastda",
        "prompt": "Vertical social-media story background. The product is centered in the middle of the frame, beautifully lit; the top fifth and the bottom quarter of the frame are calm, softly blurred and free of objects and text.",
    },
]

STYLES_BY_ID: Dict[str, Dict[str, Any]] = {s["id"]: s for s in STYLES}
DEFAULT_STYLE = "minimal_studio"


def get_style(style_id: Optional[str]) -> Dict[str, Any]:
    return STYLES_BY_ID.get(style_id or "", STYLES_BY_ID[DEFAULT_STYLE])


def needs_overlay(style_id: Optional[str]) -> bool:
    """True when the result is a poster (the server draws text over the picture)."""
    return bool(get_style(style_id).get("layout"))


def style_kind(style_id: Optional[str]) -> str:
    """"clean" (Uzum catalogue photo), "ai_text" (AI-drawn information card), "poster" (server-drawn) or "scene"."""
    style = get_style(style_id)
    if style.get("kind"):
        return style["kind"]
    return "poster" if style.get("layout") else "scene"


def layout_for(style_id: Optional[str]) -> Optional[str]:
    return get_style(style_id).get("layout")


def default_aspect(style_id: Optional[str]) -> str:
    style = get_style(style_id)
    if style.get("aspect"):
        return style["aspect"]
    layout = style.get("layout")
    return LAYOUTS[layout]["aspect"] if layout else DEFAULT_ASPECT


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
        item = {k: v for k, v in s.items() if k != "prompt"}
        layout = s.get("layout")
        item["aspect"] = s.get("aspect") or (LAYOUTS[layout]["aspect"] if layout else DEFAULT_ASPECT)
        styles.append(item)
    layouts = {k: {kk: vv for kk, vv in v.items() if kk != "space"} for k, v in LAYOUTS.items()}
    palettes = {k: {kk: vv for kk, vv in v.items() if kk in ("ru", "uz", "swatch")} for k, v in PALETTES.items()}
    return {
        "groups": GROUPS,
        "styles": styles,
        "layouts": layouts,
        "aspects": list(ASPECTS.keys()),
        "palettes": palettes,
        "default_aspect": DEFAULT_ASPECT,
        "default_palette": DEFAULT_PALETTE,
    }
