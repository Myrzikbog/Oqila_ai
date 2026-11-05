"""Prepare a ready-to-show demo account for a live presentation.

Fills the account of the given Telegram user with sample product cards and connects Uzum in
demo mode (2 shops, orders, stocks), so the app never starts from an empty screen on stage.
The account is flagged as a demo account: its data is excluded from the public /stage numbers.

Usage:
    python scripts/seed_demo.py --tg-id 123456789            # your own Telegram id
    python scripts/seed_demo.py --tg-id 123456789 --lang ru
    python scripts/seed_demo.py --tg-id 123456789 --reset    # remove previously seeded cards first

Find your Telegram id with @userinfobot. Open the bot afterwards: the Mini App shows the data.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.database import (  # noqa: E402
    get_db_connection,
    init_db,
    save_generated_card,
    set_user_terms_agreed,
    upsert_user,
)

SAMPLE_CARDS = {
    "uz": [
        {
            "title": "«Xon-atlas» — Bayramona milliy ko'ylak",
            "description": "Qo'lda tikilgan, tabiiy ipak xon-atlasdan bayramona ko'ylak. Har bir chok usta qo'li bilan.\n\n"
            "✨ Afzalliklari:\n• 100% tabiiy ipak\n• O'lchamga moslab tikiladi\n• Toshkent bo'ylab bepul yetkazib berish",
            "price_tag": "💰 Narx: 380 000 so'm",
            "hashtags": ["#xonatlas", "#milliy_libos", "#handmade", "#tadbirkor_ayollar", "#uzbekistan"],
            "marketing_tip": "Instagram'da Navro'z oldidan 'oldindan buyurtma' aksiyasini e'lon qiling.",
            "cost_price": 120_000, "desired_price": 380_000,
        },
        {
            "title": "«Rishton» — Qo'lda bo'yalgan sopol lagan",
            "description": "Rishton ustalarining an'anaviy ishqor sirli lagan. Mehmon dasturxoni uchun ajoyib sovg'a.",
            "price_tag": "💰 Narx: 240 000 so'm",
            "hashtags": ["#rishton", "#sopol", "#hunarmand", "#sovga", "#uzbekistan"],
            "marketing_tip": "To'y mavsumida sovg'a to'plamlari sifatida taklif qiling.",
            "cost_price": 90_000, "desired_price": 240_000,
        },
        {
            "title": "«Shirin» — Uy pishiriqlari to'plami",
            "description": "Bugun pishirilgan pishiriqlar: chak-chak, pishiriq va xolva. Konservantlarsiz, uy sharoitida.",
            "price_tag": "💰 Narx: 85 000 so'm",
            "hashtags": ["#uy_pishiriqlari", "#chakchak", "#tadbirkor", "#toshkent"],
            "marketing_tip": "Telegram kanalida har kuni ertalab 'bugungi menyu' postini joylang.",
            "cost_price": 35_000, "desired_price": 85_000,
        },
    ],
    "ru": [
        {
            "title": "«Хан-атлас» — Праздничное национальное платье",
            "description": "Платье ручной работы из натурального шёлкового хан-атласа. Каждый шов сделан мастерицей.\n\n"
            "✨ Преимущества:\n• 100% натуральный шёлк\n• Пошив по вашим меркам\n• Бесплатная доставка по Ташкенту",
            "price_tag": "💰 Цена: 380 000 сум",
            "hashtags": ["#ханатлас", "#национальное_платье", "#handmade", "#tadbirkor_ayollar", "#uzbekistan"],
            "marketing_tip": "Объявите в Instagram предзаказ к Навруз — праздничные платья раскупают заранее.",
            "cost_price": 120_000, "desired_price": 380_000,
        },
        {
            "title": "«Риштан» — Расписное керамическое блюдо",
            "description": "Традиционный ляган мастеров Риштана с щелочной глазурью. Отличный подарок к дастархану.",
            "price_tag": "💰 Цена: 240 000 сум",
            "hashtags": ["#риштан", "#керамика", "#ремесло", "#подарок", "#uzbekistan"],
            "marketing_tip": "В сезон свадеб предлагайте блюда как готовые подарочные наборы.",
            "cost_price": 90_000, "desired_price": 240_000,
        },
        {
            "title": "«Ширин» — Набор домашней выпечки",
            "description": "Выпечка сегодняшнего дня: чак-чак, пиширики и халва. Без консервантов, по домашним рецептам.",
            "price_tag": "💰 Цена: 85 000 сум",
            "hashtags": ["#домашняя_выпечка", "#чакчак", "#tadbirkor", "#ташкент"],
            "marketing_tip": "Публикуйте каждое утро пост «меню дня» в Telegram-канале.",
            "cost_price": 35_000, "desired_price": 85_000,
        },
    ],
}

DEMO_NOTE = "seed_demo"


def seed(tg_id: int, lang: str = "uz", name: str = "Oqila Demo", reset: bool = False) -> int:
    if tg_id <= 0:
        raise SystemExit("--tg-id must be a real (positive) Telegram user id")
    init_db()
    user = upsert_user(tg_id=tg_id, name=name, lang=lang, status="yatt", category="sewing", sales_channel="uzum")
    user_id = int(user["user_id"])
    set_user_terms_agreed(tg_id, True, lang=lang)
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET is_demo = 1 WHERE user_id = ?", (user_id,))
        if reset:
            conn.execute("DELETE FROM generated_cards WHERE user_id = ? AND note = ?", (user_id, DEMO_NOTE))
        conn.commit()

    for card in SAMPLE_CARDS[lang]:
        save_generated_card(
            title=card["title"],
            description=card["description"],
            price_tag=card["price_tag"],
            hashtags=card["hashtags"],
            marketing_tip=card["marketing_tip"],
            cost_price=card["cost_price"],
            desired_price=card["desired_price"],
            note=DEMO_NOTE,
            lang=lang,
            user_id=user_id,
            is_demo=True,
        )

    from services.uzum_service import uzum_service

    res = asyncio.run(uzum_service.connect_and_sync(user_id=user_id, is_demo=True, telegram_chat_id=tg_id))
    print(
        f"Demo account ready: user_id={user_id}, tg_id={tg_id}, "
        f"{len(SAMPLE_CARDS[lang])} sample cards, Uzum demo: {res.get('message')}"
    )
    return user_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tg-id", type=int, required=True, help="Telegram user id of the presenter")
    parser.add_argument("--lang", choices=("uz", "ru"), default="uz")
    parser.add_argument("--name", default="Oqila Demo")
    parser.add_argument("--reset", action="store_true", help="delete previously seeded sample cards first")
    args = parser.parse_args()
    seed(args.tg_id, lang=args.lang, name=args.name, reset=args.reset)
