"""
legal_kb.py — the single source of legal facts of the application.

Before this module the same facts lived in five places (the calculator, the AI prompt, the offline answer,
the FAQ and the bot). Now they live in services/legal_kb.json and everything else reads them from here:

    kb.value("brv")                      the number (derived facts are computed from their base)
    kb.render_prompt("ru", tags)         "[F:id] text (basis, source, checked <date>)" lines for the AI prompt
    kb.facts_for(question)               facts that match the words of a question
    kb.stale(90)                         facts not re-checked for 90 days
    kb.fact_text("brv", "uz")                 one fact's text with its numbers filled in

Facts are never invented: only what docs/LEGAL_VERIFICATION.md confirms is stated as fact. What is not
confirmed carries status "unverified" and the AI says "needs checking" about it.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

KB_PATH = Path(__file__).with_name("legal_kb.json")
STATUSES = ("confirmed", "secondary", "unverified")


def _fmt_int(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", " ")


def _fmt_number(value: float) -> str:
    if float(value).is_integer():
        return _fmt_int(value)
    return f"{value:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")


class KnowledgeBase:
    def __init__(self, path: Path = KB_PATH) -> None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.allowed_domains: List[str] = list(raw.get("allowed_domains", []))
        self.facts: Dict[str, Dict[str, Any]] = {f["id"]: dict(f) for f in raw["facts"]}
        self._values: Dict[str, Optional[float]] = {}
        for fact_id in self.facts:
            self._values[fact_id] = self._compute(fact_id, set())
        self._vars = self._build_vars()

    # -- values ---------------------------------------------------------------------------------
    def _compute(self, fact_id: str, seen: set) -> Optional[float]:
        if fact_id in seen:
            raise ValueError(f"circular derivation of {fact_id}")
        fact = self.facts[fact_id]
        derived = fact.get("derived")
        if not derived:
            return fact.get("value")
        base = self._compute(derived["of"], seen | {fact_id})
        if base is None:
            return None
        if "mul_fact" in derived:
            other = self._compute(derived["mul_fact"], seen | {fact_id})
            return None if other is None else round(base * other, 4)
        return round(base * derived["mul"], 4)

    def value(self, fact_id: str) -> float:
        """The numeric value of a fact. Raises KeyError for a fact that has none (texts, unverified items)."""
        value = self._values[fact_id]
        if value is None:
            raise KeyError(f"fact {fact_id!r} has no numeric value")
        return value

    def number_values(self) -> Dict[str, float]:
        return {k: v for k, v in self._values.items() if v is not None}

    def _build_vars(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for fact_id, value in self.number_values().items():
            out[fact_id] = _fmt_number(value)
            if value >= 1e9:
                out[f"{fact_id}_bn"] = _fmt_number(round(value / 1e9, 2))
        return out

    # -- texts ----------------------------------------------------------------------------------
    def fill(self, template: str) -> str:
        """Fill {fact_id} placeholders with the formatted numbers of the base."""
        return re.sub(r"\{(\w+)\}", lambda m: self._vars.get(m.group(1), m.group(0)), template)

    def fact_text(self, fact_id: str, lang: str = "ru") -> str:
        fact = self.facts[fact_id]
        return self.fill(fact["text_uz"] if lang == "uz" else fact["text_ru"])

    def fmt(self, name: str) -> str:
        """A formatted number for UI texts: kb.fmt("brv") -> "440 000", kb.fmt("threshold_uzs_bn") -> "5,28"."""
        return self._vars[name]

    def format_vars(self) -> Dict[str, str]:
        return dict(self._vars)

    # -- selection ------------------------------------------------------------------------------
    def render_prompt(self, lang: str = "ru", tags: Optional[Iterable[str]] = None, ids: Optional[Iterable[str]] = None) -> str:
        """The facts as prompt lines. Without tags or ids: all facts. Unverified facts say so."""
        wanted_tags = set(tags or [])
        wanted_ids = set(ids or [])
        lines = []
        for fact_id, fact in self.facts.items():
            if wanted_ids and fact_id not in wanted_ids:
                continue
            if wanted_tags and not (wanted_tags & set(fact["tags"])) and fact_id not in wanted_ids:
                continue
            mark = " ⚠ NOT VERIFIED: say that this needs checking" if fact["status"] == "unverified" else ""
            lines.append(
                f"[F:{fact_id}] {self.fact_text(fact_id, lang)} ({fact['legal_basis']}; {fact['source_url']}; "
                f"checked {fact['verified_at']}; {fact['status']}){mark}"
            )
        return "\n".join(lines)

    _WORDS = {
        "brv": ("брв", "bhm", "базов", "bazaviy"),
        "turnover_rate": ("налог с оборота", "оборот", "ставк", "aylanma", "stavka", "процент", "foiz"),
        "turnover_deadline_day": ("срок", "когда плат", "до какого", "muddat", "qachon to'la", "qachon tola"),
        "annual_calc_deadline": ("годов", "декларац", "yillik", "deklaratsiya", "15 февраля"),
        "exemption_100m_cancelled": ("100 млн", "освобожд", "ozod", "100 mln"),
        "threshold_brv": ("порог", "ндс", "прибыл", "qqs", "chegara", "12 000", "общий режим", "umumiy"),
        "social_tax_yatt": ("соцналог", "социальный налог", "ijtimoiy", "соц. налог", "соцвзнос"),
        "social_tax_self_employed": ("стаж", "staj", "пенси", "pensiya"),
        "fee_yatt_online": ("госпошлин", "стоит открыть", "сколько стоит", "davlat boji", "narxi"),
        "fee_yatt_cgu": ("госпошлин", "цгу", "центр госуслуг", "davlat boji"),
        "yatt_registration": ("ятт", "ип ", "открыть", "регистр", "yatt", "ro'yxatdan", "ochish", "birdarcha"),
        "ecp_person": ("эцп", "e-imzo", "эп ", "подпис", "eri", "imzo"),
        "ecp_legal": ("эцп", "e-imzo", "eri", "imzo"),
        "ecp_free_id_2026": ("эцп", "бесплатн", "eri", "bepul"),
        "self_employed_list": ("перечень", "парикмахер", "фото", "услуг", "ro'yxat", "sartarosh"),
        "self_employed_item33": ("перепрод", "китай", "опт", "рынок", "qayta sot", "xitoy", "ulgurji", "самозанят", "o'z-o'zini"),
        "self_employed_no_staff": ("нанять", "работник", "сотрудник", "xodim", "yollash"),
        "uzum_tax_agent": ("uzum", "узум", "удерж", "агент", "ushlab"),
        "kkm_rule": ("ккм", "чек", "касс", "nkm", "chek", "kassa"),
        "ecommerce_law": ("электронн", "интернет-магазин", "elektron", "tijorat"),
        "bank_account_instruction": ("счёт", "счет", "карт", "hisob", "karta", "банк", "bank"),
        "rate_1_to_5bn": ("млрд", "mlrd", "1 000 000 000"),
        "uzum_self_employed_rule": ("uzum", "узум", "самозанят", "o'z-o'zini"),
        "hunarmand": ("хунарманд", "hunarmand", "ремесл", "hunarmandchilik"),
        "ofd_receipts_click_payme": ("click", "payme", "клик", "пейми", "эквайринг"),
    }

    def facts_for(self, question: str, limit: int = 8) -> List[str]:
        """Ids of the facts that match the words of a question (keyword match, best first)."""
        q = (question or "").casefold().replace("’", "'").replace("ʻ", "'")
        scored = []
        for fact_id, words in self._WORDS.items():
            if fact_id not in self.facts:
                continue
            score = sum(1 for w in words if w in q)
            if score:
                scored.append((score, fact_id))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [fact_id for _, fact_id in scored[:limit]]

    # -- upkeep ---------------------------------------------------------------------------------
    def stale(self, days: int = 90, today: Optional[date] = None) -> List[Dict[str, Any]]:
        """Facts whose last check is older than `days`, oldest first (for the manual re-check)."""
        today = today or date.today()
        out = []
        for fact in self.facts.values():
            age = (today - datetime.strptime(fact["verified_at"], "%Y-%m-%d").date()).days
            if age > days:
                out.append({"id": fact["id"], "age_days": age, "status": fact["status"], "source_url": fact["source_url"]})
        return sorted(out, key=lambda x: -x["age_days"])

    def public(self, lang: str = "ru") -> List[Dict[str, Any]]:
        """What GET /api/legal-kb returns: texts with dates and sources (no internal fields)."""
        stale_ids = {x["id"] for x in self.stale(90)}
        return [
            {"id": f["id"], "text": self.fact_text(f["id"], lang), "legal_basis": f["legal_basis"], "source_url": f["source_url"],
             "verified_at": f["verified_at"], "status": f["status"], "stale": f["id"] in stale_ids}
            for f in self.facts.values()
        ]

    def is_allowed_domain(self, url_or_domain: str) -> bool:
        host = (urlparse(url_or_domain).hostname if "://" in url_or_domain else url_or_domain) or ""
        host = host.lower().removeprefix("www.")
        return any(host == d or host.endswith("." + d) for d in self.allowed_domains)

    # -- the offline answer ---------------------------------------------------------------------
    _MOCK_SECTIONS = (
        ("turnover_rate", "turnover_deadline_day", "uzum_tax_agent"),
        ("self_employed_list", "self_employed_item33", "social_tax_self_employed"),
        ("yatt_registration", "fee_yatt_online", "social_tax_yatt", "threshold_brv"),
        ("kkm_rule",),
    )
    _MOCK_TITLES = {
        "ru": ("Налог с оборота", "Самозанятость", "ЯТТ", "Чеки"),
        "uz": ("Aylanmadan soliq", "O'z-o'zini band qilish", "YaTT", "Cheklar"),
    }

    def offline_answer(self, lang: str = "ru") -> Dict[str, Any]:
        """A structured answer assembled from the base, for when the AI is unavailable. Not an answer to the
        question: a short reference of the verified rules, which the UI marks as a template answer."""
        lang = "uz" if lang == "uz" else "ru"
        ids = [i for section in self._MOCK_SECTIONS for i in section]
        titles = self._MOCK_TITLES[lang]
        steps = []
        for title, section in zip(titles, self._MOCK_SECTIONS, strict=True):
            steps.append(f"{title}: " + " ".join(self.fact_text(i, lang) for i in section))
        return {
            "short_answer": {"ru": "Коротко о проверенных правилах для предпринимательниц (ИИ сейчас недоступен, это шаблонный справочник, а не ответ на ваш вопрос).",
                             "uz": "Tadbirkor ayollar uchun tekshirilgan qoidalar haqida qisqacha (AI hozir mavjud emas, bu shablon ma'lumot, savolingizga javob emas)."}[lang],
            "steps": steps, "documents": [],
            "where_to_go": [{"name": "soliq.uz", "url": "https://soliq.uz"}, {"name": "my.gov.uz", "url": "https://my.gov.uz"}, {"name": "lex.uz", "url": "https://lex.uz"}],
            "deadlines": [], "costs": [], "risks": [],
            "sources": [{"title": self.facts[i]["legal_basis"], "url": self.facts[i]["source_url"], "official": self.is_allowed_domain(self.facts[i]["source_url"]) and self.facts[i]["status"] == "confirmed"} for i in ids],
            "follow_up_questions": [],
            "confidence": "low", "escalate": False, "escalate_reason": "",
        }


@lru_cache(maxsize=1)
def get_kb() -> KnowledgeBase:
    return KnowledgeBase()


kb = get_kb()
