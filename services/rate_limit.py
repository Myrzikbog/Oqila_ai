"""
rate_limit.py — Limits on AI (Gemini) usage, so one user or a crowd at a demo cannot burn the quota.

Counts are taken from usage_logs, which every AI endpoint already writes, so the limits are
shared by all uvicorn workers and survive restarts.

- Per user: hourly and daily limits per action -> the endpoint answers HTTP 429.
- Global daily budget of real Gemini calls -> once spent, the app keeps working on mock answers
  instead of failing in front of an audience.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

from services.database import get_db_connection


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Limit:
    event_types: Tuple[str, ...]
    per_hour_env: str
    per_hour_default: int
    per_day_env: str
    per_day_default: int

    @property
    def per_hour(self) -> int:
        return _env_int(self.per_hour_env, self.per_hour_default)

    @property
    def per_day(self) -> int:
        return _env_int(self.per_day_env, self.per_day_default)


LIMITS = {
    "generate_card": Limit(("generate_card",), "AI_CARD_LIMIT_PER_HOUR", 20, "AI_CARD_LIMIT_PER_DAY", 60),
    "legal_qa": Limit(("legal_qa",), "AI_LEGAL_LIMIT_PER_HOUR", 30, "AI_LEGAL_LIMIT_PER_DAY", 100),
    "demo_card": Limit(("demo_card",), "DEMO_CARD_LIMIT_PER_HOUR", 30, "DEMO_CARD_LIMIT_PER_DAY", 100),
}

AI_EVENT_TYPES = ("generate_card", "legal_qa")

MESSAGES = {
    "uz": "Juda ko'p so'rov yuborildi. Iltimos, {wait} keyinroq qayta urinib ko'ring.",
    "ru": "Слишком много запросов. Пожалуйста, попробуйте снова {wait}.",
}
WAIT = {
    "hour": {"uz": "bir soatdan", "ru": "через час"},
    "day": {"uz": "ertaga", "ru": "завтра"},
}


def _count(event_types: Tuple[str, ...], since: str, user_id: Optional[int] = None, real_only: bool = False) -> int:
    placeholders = ",".join("?" for _ in event_types)
    query = f"SELECT COUNT(*) FROM usage_logs WHERE event_type IN ({placeholders}) AND created_at >= datetime('now', ?)"
    params: list = [*event_types, since]
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    if real_only:
        query += " AND is_mock = 0"
    with get_db_connection() as conn:
        return int(conn.execute(query, params).fetchone()[0])


def check_user_limit(action: str, user_id: int, lang: str = "ru") -> Optional[str]:
    """Return a localized error message when the user exceeded the limit for `action`, else None."""
    limit = LIMITS[action]
    lang = "uz" if lang == "uz" else "ru"
    if limit.per_hour > 0 and _count(limit.event_types, "-1 hour", user_id) >= limit.per_hour:
        return MESSAGES[lang].format(wait=WAIT["hour"][lang])
    if limit.per_day > 0 and _count(limit.event_types, "-1 day", user_id) >= limit.per_day:
        return MESSAGES[lang].format(wait=WAIT["day"][lang])
    return None


def global_ai_budget_exhausted() -> bool:
    """True when today's budget of real Gemini calls (AI_GLOBAL_DAILY_LIMIT, 0 = unlimited) is spent."""
    budget = _env_int("AI_GLOBAL_DAILY_LIMIT", 1000)
    if budget <= 0:
        return False
    return _count(AI_EVENT_TYPES, "-1 day", real_only=True) >= budget
