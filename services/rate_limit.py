"""
rate_limit.py — Limits on AI (Gemini) usage, so one user or a crowd at a demo cannot burn the quota.

Three independent counters, all in SQLite so they are shared by every uvicorn worker and survive restarts:

- ai_reservations: one row per user request that may spend AI quota. The row is inserted ("pending") inside a
  BEGIN IMMEDIATE transaction *before* the AI is called and turned into "ok" or "failed" afterwards, so N parallel
  requests cannot slip past the limit and a crash between the call and the bookkeeping cannot give free retries.
  The user limit counts "ok" + "pending"; a separate attempts limit (3x) also counts "failed".
- ai_calls: one row per real Gemini call (text / image / ocr / legal). The global daily budget
  (AI_GLOBAL_DAILY_LIMIT, 0 = unlimited) is counted on it: one card is up to 7 calls, not 1.
- usage_logs: still used for cheap non-AI limits (demo card) and for the limit of guest accounts per IP.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from services.database import get_db_connection

logger = logging.getLogger("oqila_limits")

ATTEMPTS_FACTOR = 3  # failed attempts are free for the user, but only up to 3x the normal limit
PENDING_TTL_MINUTES = 15  # a "pending" row older than this belongs to a crashed request: treated as failed
GUESTS_PER_IP_PER_HOUR = 5
AI_CALL_KINDS = ("text", "image", "ocr", "legal")


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
    # Poster edits are drawn locally (no AI), so the limit only guards the CPU
    "poster_render": Limit(("poster_render",), "POSTER_RENDER_LIMIT_PER_HOUR", 400, "POSTER_RENDER_LIMIT_PER_DAY", 3000),
}

# Actions that spend AI quota: limited through reserve(), reported by GET /api/limits
AI_ACTIONS = ("generate_card", "legal_qa")

MESSAGES = {
    "uz": "Juda ko'p so'rov yuborildi. Iltimos, {wait} keyinroq qayta urinib ko'ring.",
    "ru": "Слишком много запросов. Пожалуйста, попробуйте снова {wait}.",
}
WAIT = {
    "hour": {"uz": "bir soatdan", "ru": "через час"},
    "day": {"uz": "ertaga", "ru": "завтра"},
}


class LimitExceeded(Exception):
    """The user has no quota left for this action; str(exc) is a localized message for the user."""


def _message(window: str, lang: str) -> str:
    lang = "uz" if lang == "uz" else "ru"
    return MESSAGES[lang].format(wait=WAIT[window][lang])


# ---------------------------------------------------------------------------
# Cheap limits counted on usage_logs (no AI involved)
# ---------------------------------------------------------------------------
def _count(event_types: Tuple[str, ...], since: str, user_id: Optional[int] = None) -> int:
    placeholders = ",".join("?" for _ in event_types)
    query = f"SELECT COUNT(*) FROM usage_logs WHERE event_type IN ({placeholders}) AND created_at >= datetime('now', ?)"
    params: list = [*event_types, since]
    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)
    with closing(get_db_connection()) as conn:
        return int(conn.execute(query, params).fetchone()[0])


def check_user_limit(action: str, user_id: int, lang: str = "ru") -> Optional[str]:
    """Return a localized error message when the user exceeded the limit for a non-AI `action`, else None."""
    limit = LIMITS[action]
    if limit.per_hour > 0 and _count(limit.event_types, "-1 hour", user_id) >= limit.per_hour:
        return _message("hour", lang)
    if limit.per_day > 0 and _count(limit.event_types, "-1 day", user_id) >= limit.per_day:
        return _message("day", lang)
    return None


# ---------------------------------------------------------------------------
# AI reservations
# ---------------------------------------------------------------------------
_USED = f"(status = 'ok' OR (status = 'pending' AND created_at >= datetime('now', '-{PENDING_TTL_MINUTES} minutes')))"


def _window_counts(conn: sqlite3.Connection, user_id: int, action: str, since: str) -> Tuple[int, int]:
    """(used, attempts) of the user's reservations for `action` in the window."""
    row = conn.execute(
        f"SELECT COALESCE(SUM(CASE WHEN {_USED} THEN 1 ELSE 0 END), 0), COUNT(*) FROM ai_reservations "
        "WHERE user_id = ? AND event_type = ? AND created_at >= datetime('now', ?)",
        (user_id, action, since),
    ).fetchone()
    return int(row[0]), int(row[1])


def reserve(action: str, user_id: int, lang: str = "ru") -> int:
    """Atomically take one unit of the user's quota for `action`. Returns the reservation id to pass to finish().

    Raises LimitExceeded with a localized message when the hourly/daily limit (ok + pending) or the attempts
    limit (ok + pending + failed, 3x the normal one) is reached.
    """
    limit = LIMITS[action]
    conn = get_db_connection()
    try:
        conn.isolation_level = None  # explicit transaction control
        conn.execute("BEGIN IMMEDIATE")
        try:
            for window, since, cap in (("hour", "-1 hour", limit.per_hour), ("day", "-1 day", limit.per_day)):
                if cap <= 0:
                    continue
                used, attempts = _window_counts(conn, user_id, action, since)
                if used >= cap or attempts >= cap * ATTEMPTS_FACTOR:
                    conn.execute("ROLLBACK")
                    raise LimitExceeded(_message(window, lang))
            cur = conn.execute(
                "INSERT INTO ai_reservations (user_id, event_type, status) VALUES (?, ?, 'pending')", (user_id, action)
            )
            conn.execute("COMMIT")
            return int(cur.lastrowid)
        except LimitExceeded:
            raise
        except Exception:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
    finally:
        conn.close()


def finish(reservation_id: Optional[int], ok: bool) -> None:
    """Close a reservation: "ok" spends the user's quota, "failed" gives it back (it still counts as an attempt)."""
    if not reservation_id:
        return
    try:
        with closing(get_db_connection()) as conn:
            conn.execute(
                "UPDATE ai_reservations SET status = ? WHERE id = ? AND status = 'pending'",
                ("ok" if ok else "failed", reservation_id),
            )
            conn.commit()
    except Exception as exc:  # the row stays "pending" and expires on its own
        logger.warning("Could not close AI reservation %s: %s", reservation_id, exc)


def limits_status(user_id: int) -> Dict[str, Dict[str, Any]]:
    """What GET /api/limits returns: per AI action the daily usage, the hourly usage and when a slot frees up."""
    out: Dict[str, Dict[str, Any]] = {}
    with closing(get_db_connection()) as conn:
        for action in AI_ACTIONS:
            limit = LIMITS[action]
            used_day, _ = _window_counts(conn, user_id, action, "-1 day")
            used_hour, _ = _window_counts(conn, user_id, action, "-1 hour")
            hour_full = limit.per_hour > 0 and used_hour >= limit.per_hour
            day_full = limit.per_day > 0 and used_day >= limit.per_day
            resets_at = None
            if hour_full or day_full:
                # the oldest counted reservation of the blocking window leaves it first
                since, delta = ("-1 day", timedelta(days=1)) if day_full else ("-1 hour", timedelta(hours=1))
                row = conn.execute(
                    f"SELECT MIN(created_at) FROM ai_reservations WHERE user_id = ? AND event_type = ? "
                    f"AND created_at >= datetime('now', ?) AND {_USED}",
                    (user_id, action, since),
                ).fetchone()
                if row and row[0]:
                    oldest = datetime.strptime(row[0][:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    resets_at = (oldest + delta).isoformat(timespec="seconds")
            out[action] = {
                "used": used_day, "limit": limit.per_day, "resets_at": resets_at,
                "hour": {"used": used_hour, "limit": limit.per_hour},
            }
    return out


# ---------------------------------------------------------------------------
# Real Gemini calls and the global daily budget
# ---------------------------------------------------------------------------
def record_ai_call(kind: str, model: str = "") -> None:
    """Count one real request to Gemini (called right before the request is sent)."""
    try:
        with closing(get_db_connection()) as conn:
            conn.execute("INSERT INTO ai_calls (kind, model) VALUES (?, ?)", (kind if kind in AI_CALL_KINDS else "text", model))
            conn.commit()
    except Exception as exc:
        logger.warning("Could not count an AI call: %s", exc)


def ai_calls_today() -> int:
    with closing(get_db_connection()) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM ai_calls WHERE created_at >= datetime('now', '-1 day')").fetchone()[0])


def global_ai_budget_exhausted() -> bool:
    """True when today's budget of real Gemini calls (AI_GLOBAL_DAILY_LIMIT, 0 = unlimited) is spent."""
    budget = _env_int("AI_GLOBAL_DAILY_LIMIT", 1000)
    if budget <= 0:
        return False
    try:
        return ai_calls_today() >= budget
    except Exception as exc:
        logger.warning("Could not read the AI budget: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Guest accounts per IP
# ---------------------------------------------------------------------------
def register_guest(ip: str) -> bool:
    """Count a new guest account for this IP. False when the IP already created GUESTS_PER_IP_PER_HOUR in the last hour."""
    cap = _env_int("GUESTS_PER_IP_PER_HOUR", GUESTS_PER_IP_PER_HOUR)
    if cap <= 0:
        return True
    details = json.dumps({"ip": ip or "unknown"})
    conn = get_db_connection()
    try:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        count = conn.execute(
            "SELECT COUNT(*) FROM usage_logs WHERE event_type = 'guest_create' AND details = ? "
            "AND created_at >= datetime('now', '-1 hour')",
            (details,),
        ).fetchone()[0]
        if count >= cap:
            conn.execute("ROLLBACK")
            return False
        conn.execute("INSERT INTO usage_logs (event_type, lang, is_mock, details) VALUES ('guest_create', '', 0, ?)", (details,))
        conn.execute("COMMIT")
        return True
    finally:
        conn.close()
