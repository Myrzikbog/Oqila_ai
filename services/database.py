"""
database.py — SQLite Logger & Metrics for Oqila AI
Tracks usage events (AI generations, calculations, legal queries, bot interactions)
for hackathon demonstration and analytics.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("oqila_db")

DB_PATH = Path(__file__).parent.parent / "oqila_ai.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_db() -> None:
    """Initialize database tables if they do not exist."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    lang TEXT DEFAULT 'ru',
                    is_mock INTEGER DEFAULT 0,
                    details TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS generated_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    title TEXT NOT NULL,
                    description TEXT,
                    price_tag TEXT,
                    hashtags TEXT,
                    marketing_tip TEXT,
                    studio_photo_url TEXT,
                    photoshoot_style TEXT,
                    content_tone TEXT,
                    content_format TEXT,
                    cost_price REAL,
                    desired_price REAL,
                    note TEXT,
                    lang TEXT DEFAULT 'ru',
                    is_favorite INTEGER DEFAULT 0
                )
            """)
            # Migration check: add is_favorite column if missing from existing database
            try:
                cursor.execute("ALTER TABLE generated_cards ADD COLUMN is_favorite INTEGER DEFAULT 0")
            except Exception:
                pass  # Already exists

            # Bot subscribers for daily tips and tax reminders
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_subscribers (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT,
                    lang TEXT DEFAULT 'uz',
                    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_event_type ON usage_logs(event_type);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON usage_logs(created_at);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_created_at ON generated_cards(created_at);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_card_fav ON generated_cards(is_favorite);
            """)
            conn.commit()
            logger.info("SQLite database initialized at %s", DB_PATH)
    except Exception as exc:
        logger.error("Failed to initialize database: %s", exc)


def log_event(
    event_type: str,
    lang: str = "ru",
    is_mock: bool = False,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an interaction or API call."""
    try:
        details_json = json.dumps(details, ensure_ascii=False) if details else "{}"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO usage_logs (event_type, lang, is_mock, details)
                VALUES (?, ?, ?, ?)
                """,
                (event_type, lang, 1 if is_mock else 0, details_json),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("Could not log event %s: %s", event_type, exc)


def get_stats() -> Dict[str, Any]:
    """Return aggregated statistics for hackathon demo."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total FROM usage_logs")
            total = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT event_type, COUNT(*) AS count 
                FROM usage_logs 
                GROUP BY event_type
            """)
            events_by_type = {row["event_type"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT lang, COUNT(*) AS count 
                FROM usage_logs 
                GROUP BY lang
            """)
            by_lang = {row["lang"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT is_mock, COUNT(*) AS count 
                FROM usage_logs 
                GROUP BY is_mock
            """)
            mock_counts = {bool(row["is_mock"]): row["count"] for row in cursor.fetchall()}

            cursor.execute("""
                SELECT id, created_at, event_type, lang, is_mock, details
                FROM usage_logs
                ORDER BY id DESC
                LIMIT 10
            """)
            recent_logs = []
            for row in cursor.fetchall():
                try:
                    det = json.loads(row["details"]) if row["details"] else {}
                except Exception:
                    det = row["details"]
                recent_logs.append({
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "event_type": row["event_type"],
                    "lang": row["lang"],
                    "is_mock": bool(row["is_mock"]),
                    "details": det,
                })

            return {
                "total_events": total,
                "events_by_type": events_by_type,
                "by_lang": by_lang,
                "real_ai_count": mock_counts.get(False, 0),
                "mock_count": mock_counts.get(True, 0),
                "recent_logs": recent_logs,
            }
    except Exception as exc:
        logger.error("Could not fetch stats: %s", exc)
        return {
            "total_events": 0,
            "events_by_type": {},
            "by_lang": {},
            "real_ai_count": 0,
            "mock_count": 0,
            "recent_logs": [],
        }


def save_generated_card(
    title: str,
    description: str,
    price_tag: str,
    hashtags: Any,
    marketing_tip: str,
    studio_photo_url: Optional[str] = None,
    photoshoot_style: Optional[str] = None,
    content_tone: Optional[str] = None,
    content_format: Optional[str] = None,
    cost_price: Optional[float] = None,
    desired_price: Optional[float] = None,
    note: Optional[str] = None,
    lang: str = "ru",
) -> int:
    """Save a generated product card to the database for history."""
    try:
        hashtags_json = json.dumps(hashtags, ensure_ascii=False) if isinstance(hashtags, list) else (hashtags or "[]")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO generated_cards (
                    title, description, price_tag, hashtags, marketing_tip,
                    studio_photo_url, photoshoot_style, content_tone, content_format,
                    cost_price, desired_price, note, lang
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title, description, price_tag, hashtags_json, marketing_tip,
                    studio_photo_url, photoshoot_style, content_tone, content_format,
                    cost_price, desired_price, note, lang
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0
    except Exception as exc:
        logger.error("Failed to save generated card: %s", exc)
        return 0


def get_history(
    limit: int = 50,
    offset: int = 0,
    favorites_only: bool = False,
    search: str = "",
) -> List[Dict[str, Any]]:
    """Retrieve generated product cards with search, favorites filtering, and pagination."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, created_at, title, description, price_tag, hashtags,
                       marketing_tip, studio_photo_url, photoshoot_style,
                       content_tone, content_format, cost_price, desired_price,
                       note, lang, is_favorite
                FROM generated_cards
                WHERE 1=1
            """
            params: list[Any] = []
            if favorites_only:
                query += " AND is_favorite = 1"
            if search.strip():
                query += " AND (title LIKE ? OR description LIKE ? OR note LIKE ? OR hashtags LIKE ?)"
                kw = f"%{search.strip()}%"
                params.extend([kw, kw, kw, kw])
            
            query += " ORDER BY is_favorite DESC, id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            items = []
            for row in cursor.fetchall():
                try:
                    ht = json.loads(row["hashtags"]) if row["hashtags"] else []
                except Exception:
                    ht = []
                items.append({
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "title": row["title"],
                    "description": row["description"],
                    "price_tag": row["price_tag"],
                    "hashtags": ht,
                    "marketing_tip": row["marketing_tip"],
                    "studio_photo_url": row["studio_photo_url"],
                    "photoshoot_style": row["photoshoot_style"],
                    "content_tone": row["content_tone"],
                    "content_format": row["content_format"],
                    "cost_price": row["cost_price"],
                    "desired_price": row["desired_price"],
                    "note": row["note"],
                    "lang": row["lang"],
                    "is_favorite": bool(row["is_favorite"]),
                })
            return items
    except Exception as exc:
        logger.error("Failed to fetch history: %s", exc)
        return []


def toggle_favorite(card_id: int) -> Optional[bool]:
    """Toggle the is_favorite state of a card. Returns the new state, or None on failure."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_favorite FROM generated_cards WHERE id = ?", (card_id,))
            row = cursor.fetchone()
            if not row:
                return None
            new_val = 0 if row["is_favorite"] else 1
            cursor.execute("UPDATE generated_cards SET is_favorite = ? WHERE id = ?", (new_val, card_id))
            conn.commit()
            return bool(new_val)
    except Exception as exc:
        logger.error("Failed to toggle favorite: %s", exc)
        return None


def save_subscriber(chat_id: int, username: str = "", lang: str = "uz") -> bool:
    """Save or update a Telegram subscriber."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO bot_subscribers (chat_id, username, lang, is_active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(chat_id) DO UPDATE SET is_active = 1, lang = excluded.lang, username = excluded.username
                """,
                (chat_id, username, lang),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save subscriber: %s", exc)
        return False


def get_subscribers() -> List[Dict[str, Any]]:
    """Return all active bot subscribers."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT chat_id, username, lang FROM bot_subscribers WHERE is_active = 1")
            return [dict(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.error("Failed to fetch subscribers: %s", exc)
        return []


def delete_history_item(card_id: int) -> bool:
    """Delete a generated card by ID from history."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM generated_cards WHERE id = ?", (card_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to delete history item: %s", exc)
        return False


def clear_history() -> bool:
    """Clear all generated cards from history."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM generated_cards")
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to clear history: %s", exc)
        return False


# Auto-initialize on module load
init_db()
