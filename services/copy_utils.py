"""
copy_utils.py — small text helpers shared by the card pipeline: price formatting and the short
copy (title, price, benefits) derived from a generated card.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


def _clean(value: Any, limit: int) -> str:
    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())[:limit]


_EMOJI = re.compile("[\U00010000-\U0010ffff☀-➿️‍]+")


def _strip_emoji(text: str) -> str:
    return " ".join(_EMOJI.sub("", text or "").split())


def format_price(value: Any, lang: str) -> str:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return ""
    if amount <= 0:
        return ""
    return f"{amount:,.0f}".replace(",", " ") + (" so'm" if lang == "uz" else " сум")


_AMOUNT = re.compile(r"\d[\d\s\u00a0.,]*\d|\d")


def _price_from_tag(tag: str, lang: str) -> str:
    """'380 000 – 420 000 сум' -> 'от 380 000 сум'; '380 000 сум' -> '380 000 сум'; no number -> ''."""
    amounts = []
    for m in _AMOUNT.finditer(tag):
        digits = re.sub(r"\D", "", m.group(0))
        if digits:
            amounts.append(int(digits))
    if not amounts:
        return ""
    price = format_price(amounts[0], lang)
    if len(amounts) > 1 and amounts[1] != amounts[0]:
        return f"{amounts[0]:,}".replace(",", " ") + " so'mdan" if lang == "uz" else "от " + price
    return price


def default_copy(card: Dict[str, Any], desired_price: Any, lang: str) -> Dict[str, Any]:
    """Short text for a picture, taken from the generated card: title, price and up to three benefits.
    The price comes from the seller's form (or the card's own price tag): it is never invented here."""
    title = _strip_emoji(card.get("title", ""))
    if title.startswith(("«", '"', "“", "'")):
        title = re.sub(r"[«»“”\"]", "", title)  # AI titles often start with a quoted name: drop the stray marks
    title = title.strip(" -–—")
    price = format_price(desired_price, lang) or _price_from_tag(_strip_emoji(card.get("price_tag", "")), lang)
    short: List[str] = []
    long: List[str] = []
    for raw in (card.get("description") or "").splitlines():
        line = raw.strip()
        if line.startswith(("•", "-", "–", "✅", "✔")):
            text = _strip_emoji(line.lstrip("•-–✅✔ ").strip())
            if 3 <= len(text) <= 48:
                short.append(text)
            elif 48 < len(text) <= 70:
                long.append(text)
    bullets = (short + long)[:3]  # short benefits read best on a poster
    return {
        "title": _clean(title, 90),
        "price": _clean(price, 28),
        "bullets": bullets,
    }
