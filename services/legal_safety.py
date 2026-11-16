"""
legal_safety.py — what the legal assistant does NOT answer with the AI. A keyword classifier (RU and UZ, no model call)
runs before anything is sent to the model.

  evasion    "how not to pay tax / hide income": refused with the legal options instead
  sensitive  criminal cases, tax audits, frozen accounts, court: a general answer and a pointer to a lawyer (escalate)
  offtopic   clearly not about business and law: a short refusal
  ok         everything else
"""
from __future__ import annotations

import re
from typing import Dict

EVASION = re.compile(
    r"как\s+не\s+плат|не\s+плат\w*\s+налог|скрыть\s+(?:свой\s+)?(?:доход|выруч|оборот)|скрыт\w*\s+доход|уйти\s+от\s+налог|"
    r"уклон\w+\s+от\s+налог|занизить\s+(?:доход|выруч|оборот)|обнал|чёрн\w+\s+бухгалтер|черн\w+\s+бухгалтер|без\s+налогов\s+работать|"
    r"(?:скры|занизи)\w*.{0,20}(?:доход|выруч|оборот)|(?:daromad|tushum)\w*.{0,20}yashir|yashir\w*.{0,20}(?:daromad|tushum)|"
    r"soliq\s+to['’ʻ]?lama|soliqdan\s+qoch|soliqni\s+to['’ʻ]?lamaslik|daromadni\s+yashir|tushumni\s+yashir|yashirin\s+(?:ishlash|daromad)|soliqsiz\s+ishla",
    re.IGNORECASE,
)
SENSITIVE = re.compile(
    r"уголовн|арест\w*\s+(?:сч[её]т|имуществ)|заблокир\w+\s+сч[её]т|налогов\w+\s+проверк|проверк\w+\s+(?:налог|гнк)|прокуратур|в\s+суд|суд\s|иск\s|задержан|"
    r"привлеч\w+\s+к\s+ответственност|jinoyat|hisob(?:varaq)?\w*\s+(?:bloklan|hibsga)|soliq\s+tekshiruv|tekshiruv|prokuratura|sudga|sud\s|qamoq|hibsga",
    re.IGNORECASE,
)
OFFTOPIC = re.compile(
    r"рецепт|погод|анекдот|стих\w*\s|гороскоп|футбол|напиши\s+(?:код|программ)|write\s+(?:code|a\s+poem)|python|javascript|курс\s+доллар|"
    r"retsept|ob-havo|latifa|she['’ʻ]?r\s+yoz|goroskop|futbol",
    re.IGNORECASE,
)
DOMAIN = re.compile(
    r"налог|ятт|\bип\b|самозан|uzum|узум|регистр|ккм|чек|эцп|бизнес|сч[её]т|штраф|брв|ндс|лиценз|товар|продаж|закон|предпринимат|ремесл|"
    r"soliq|yatt|o['’ʻ]?z-o['’ʻ]?zini|ro['’ʻ]?yxat|nkm|chek|eri|biznes|hisob|jarima|bhm|qqs|litsenziya|tovar|sotuv|qonun|tadbirkor|hunar",
    re.IGNORECASE,
)

MESSAGES: Dict[str, Dict[str, Dict[str, str]]] = {
    "evasion": {
        "ru": {"short": "С тем, как не платить налоги или скрыть доход, я помогать не буду: это нарушение закона. Зато могу рассказать, как платить меньше легально: выбрать подходящий статус (самозанятая или ЯТТ) и правильно считать налог с оборота.",
               "reason": "Вопрос про сокрытие дохода"},
        "uz": {"short": "Soliq to'lamaslik yoki daromadni yashirishda yordam bermayman: bu qonunbuzarlik. Lekin qonuniy yo'l bilan kamroq to'lashni aytib bera olaman: mos maqomni (o'z-o'zini band qilgan yoki YaTT) tanlash va aylanma solig'ini to'g'ri hisoblash.",
               "reason": "Daromadni yashirish haqida savol"},
    },
    "sensitive": {
        "ru": {"short": "Это серьёзная ситуация, и по ней нужна консультация юриста. Ниже общие сведения, но не конкретные указания: не отвечайте на требования и не подписывайте бумаги, пока не проконсультировались.",
               "reason": "Уголовное, налоговое или судебное дело"},
        "uz": {"short": "Bu jiddiy vaziyat, buning uchun yurist maslahati kerak. Quyida umumiy ma'lumot, aniq ko'rsatmalar emas: maslahatlashmasdan turib talablarga javob bermang va hujjatlarni imzolamang.",
               "reason": "Jinoiy, soliq yoki sud ishi"},
    },
    "offtopic": {
        "ru": {"short": "Я помогаю только с вопросами о бизнесе, налогах и регистрации в Узбекистане. Задайте вопрос на эту тему, например: «Какой налог платит самозанятая на Uzum?»", "reason": ""},
        "uz": {"short": "Men faqat O'zbekistondagi biznes, soliq va ro'yxatdan o'tish savollariga yordam beraman. Shu mavzuda savol bering, masalan: «Uzumda o'z-o'zini band qilgan qancha soliq to'laydi?»", "reason": ""},
    },
}


def classify(question: str, has_history: bool = False) -> str:
    """"evasion" | "sensitive" | "offtopic" | "ok"."""
    q = (question or "").replace(" ", " ")
    if EVASION.search(q):
        return "evasion"
    if SENSITIVE.search(q):
        return "sensitive"
    if OFFTOPIC.search(q) and not DOMAIN.search(q) and not has_history:
        return "offtopic"
    return "ok"
