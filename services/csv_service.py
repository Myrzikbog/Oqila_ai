"""
csv_service.py — Clean, localized and Excel-friendly CSV generator for Oqila AI.
Features:
- Encoded with UTF-8 Byte Order Mark (BOM: \ufeff) for flawless rendering in Excel (no Cyrillic mojibake).
- Semicolon (;) delimiter for native column alignment in Russian/Uzbek/European Excel.
- Human-readable localized column titles and descriptive status badges.
- Safe escaping of quotes, semicolons, and newlines.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List

STATUS_TRANSLATIONS = {
    "self_employed": "Самозанятая (1% налог)",
    "yatt": "ЯТТ (Индивидуальный предприниматель)",
    "planning": "Выбирает статус",
}

CATEGORY_TRANSLATIONS = {
    "sewing": "Пошив одежды и текстиль",
    "crafts": "Ремесло и Handmade",
    "food": "Кулинария и выпечка",
    "resale": "Перепродажа (Китай, опт)",
    "services": "Сфера услуг и бьюти",
}

CHANNEL_TRANSLATIONS = {
    "uzum": "Uzum Market",
    "instagram": "Instagram",
    "telegram": "Telegram (канал/бот)",
    "offline": "Офлайн-магазин / Точка",
}

LANG_TRANSLATIONS = {
    "ru": "Русский",
    "uz": "O'zbekcha",
}


def generate_users_csv(users: List[Dict[str, Any]]) -> bytes:
    """
    Generate a clean, professional, Excel-compatible CSV export of users.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # Column Headers
    headers = [
        "№",
        "ID в системе",
        "Telegram ID",
        "Username в Telegram",
        "Имя / Бренд",
        "Правовой статус",
        "Сфера бизнеса (Ниша)",
        "Основная площадка продаж",
        "Язык интерфейса",
        "Создано AI-карточек",
        "Подписка на бота",
        "Статус аккаунта",
        "Дата регистрации",
        "Последняя активность",
    ]
    writer.writerow(headers)

    for index, u in enumerate(users, start=1):
        raw_status = u.get("status") or "planning"
        status_label = STATUS_TRANSLATIONS.get(raw_status, raw_status)

        raw_cat = u.get("category") or "sewing"
        cat_label = CATEGORY_TRANSLATIONS.get(raw_cat, raw_cat)

        raw_channel = u.get("sales_channel") or "uzum"
        channel_label = CHANNEL_TRANSLATIONS.get(raw_channel, raw_channel)

        raw_lang = u.get("lang") or "uz"
        lang_label = LANG_TRANSLATIONS.get(raw_lang, raw_lang)

        is_sub = "Да (Активна)" if u.get("is_subscriber") else "Нет"
        is_act = "Активен" if u.get("is_active") else "Заблокирован"

        username = f"@{u['tg_username']}" if u.get("tg_username") else "—"
        name = u.get("name") or u.get("tg_first_name") or "Без имени"

        created = str(u.get("created_at") or "")[:19]
        last_seen = str(u.get("last_seen_at") or "")[:19]

        writer.writerow([
            index,
            u.get("user_id", ""),
            u.get("tg_id", "") or "Веб-гость",
            username,
            name,
            status_label,
            cat_label,
            channel_label,
            lang_label,
            u.get("cards_count", 0),
            is_sub,
            is_act,
            created,
            last_seen,
        ])

    # Prepend UTF-8 BOM (\ufeff) so Microsoft Excel natively opens as UTF-8
    csv_text = "\ufeff" + output.getvalue()
    return csv_text.encode("utf-8")


def generate_cards_csv(cards: List[Dict[str, Any]]) -> bytes:
    """
    Generate an Excel-compatible CSV of all generated product cards.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    headers = [
        "№",
        "ID карточки",
        "ID автора",
        "Автор / Бренд",
        "Telegram никнейм",
        "Название товара",
        "Ценник / Цена",
        "Себестоимость",
        "Желаемая цена",
        "Стиль съёмки",
        "Тон текста",
        "Формат публикации",
        "Хэштеги",
        "Маркетинговый совет",
        "В избранном",
        "Дата создания",
    ]
    writer.writerow(headers)

    for index, c in enumerate(cards, start=1):
        ht = ", ".join(c.get("hashtags") or []) if isinstance(c.get("hashtags"), list) else str(c.get("hashtags") or "")
        author = c.get("user_name") or c.get("tg_username") or (f"Юзер #{c.get('user_id')}" if c.get("user_id") else "Аноним")
        tg = f"@{c['tg_username']}" if c.get("tg_username") else "—"

        writer.writerow([
            index,
            c.get("id", ""),
            c.get("user_id", "") or "—",
            author,
            tg,
            c.get("title", ""),
            c.get("price_tag", ""),
            c.get("cost_price", "") or "—",
            c.get("desired_price", "") or "—",
            c.get("photoshoot_style", ""),
            c.get("content_tone", ""),
            c.get("content_format", ""),
            ht,
            c.get("marketing_tip", ""),
            "Да" if c.get("is_favorite") else "Нет",
            str(c.get("created_at") or "")[:19],
        ])

    csv_text = "\ufeff" + output.getvalue()
    return csv_text.encode("utf-8")
