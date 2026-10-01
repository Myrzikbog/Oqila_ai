"""
database.py — SQLite Logger & Metrics for Oqila AI
Tracks usage events (AI generations, calculations, legal queries, bot interactions)
for hackathon demonstration and analytics.
"""
from __future__ import annotations

import json
import logging
import os
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


_db_initialized = False


def init_db(force: bool = False) -> None:
    """Initialize database tables if they do not exist."""
    global _db_initialized
    if _db_initialized and not force:
        return
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

            # Users table: profile and identity
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER UNIQUE,
                    tg_username TEXT,
                    tg_first_name TEXT,
                    name TEXT,
                    status TEXT DEFAULT 'self_employed',
                    category TEXT DEFAULT 'sewing',
                    sales_channel TEXT DEFAULT 'uzum',
                    lang TEXT DEFAULT 'uz',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    is_admin INTEGER DEFAULT 0
                )
            """)

            # Soft migrations for users and entities
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE users ADD COLUMN agreed_terms INTEGER DEFAULT 0")
            except Exception:
                pass

            for table in ("generated_cards", "usage_logs", "bot_subscribers"):
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(user_id)")
                except Exception:
                    pass

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

            # ---------------------------------------------------------------
            # Uzum Market Tables (Multi-Shop, Orders, Stocks, Notifications)
            # ---------------------------------------------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uzum_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    api_key TEXT,
                    is_connected INTEGER DEFAULT 0,
                    is_demo INTEGER DEFAULT 0,
                    notifications_enabled INTEGER DEFAULT 1,
                    low_stock_threshold INTEGER DEFAULT 3,
                    telegram_chat_id INTEGER,
                    last_sync_at TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT OR IGNORE INTO uzum_settings (id, is_connected, is_demo, notifications_enabled, low_stock_threshold)
                VALUES (1, 0, 0, 1, 3)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uzum_shops (
                    shop_id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    legal_name TEXT,
                    inn TEXT,
                    status TEXT DEFAULT 'ACTIVE',
                    is_selected INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uzum_orders (
                    order_id INTEGER PRIMARY KEY,
                    shop_id INTEGER NOT NULL,
                    shop_title TEXT,
                    posting_number TEXT,
                    status TEXT NOT NULL,
                    status_label_ru TEXT,
                    status_label_uz TEXT,
                    total_amount REAL DEFAULT 0,
                    delivery_type TEXT DEFAULT 'FBS',
                    customer_name TEXT,
                    delivery_city TEXT,
                    created_at TIMESTAMP,
                    deadline_to_confirm TIMESTAMP,
                    is_notified INTEGER DEFAULT 0,
                    raw_json TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uzum_order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    sku_id INTEGER NOT NULL,
                    product_title TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    price REAL DEFAULT 0,
                    barcode TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uzum_stocks (
                    sku_id INTEGER PRIMARY KEY,
                    shop_id INTEGER NOT NULL,
                    shop_title TEXT,
                    product_title TEXT NOT NULL,
                    barcode TEXT,
                    current_stock INTEGER DEFAULT 0,
                    price REAL DEFAULT 0,
                    is_low_stock INTEGER DEFAULT 0,
                    cost_price REAL DEFAULT 0,
                    fbo_stock INTEGER DEFAULT 0,
                    daily_sales_velocity REAL DEFAULT 1.5,
                    last_synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Soft migrations for existing tables
            for col, col_def in [
                ("cost_price", "REAL DEFAULT 0"),
                ("fbo_stock", "INTEGER DEFAULT 0"),
                ("daily_sales_velocity", "REAL DEFAULT 1.5"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE uzum_stocks ADD COLUMN {col} {col_def}")
                except Exception:
                    pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uzum_notifications_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    shop_id INTEGER,
                    order_id INTEGER,
                    message TEXT,
                    sent_to_chat_id INTEGER,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'sent'
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
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_uzum_orders_shop ON uzum_orders(shop_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_uzum_orders_status ON uzum_orders(status);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_uzum_orders_notified ON uzum_orders(is_notified);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_uzum_stocks_shop ON uzum_stocks(shop_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_tg_id ON users(tg_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_cards_user_id ON generated_cards(user_id);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_user_id ON usage_logs(user_id);
            """)
            conn.commit()
            _db_initialized = True
            logger.info("SQLite database initialized at %s", DB_PATH)
    except Exception as exc:
        logger.error("Failed to initialize database: %s", exc)


def log_event(
    event_type: str,
    lang: str = "ru",
    is_mock: bool = False,
    details: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None,
) -> None:
    """Log an interaction or API call with optional user_id."""
    try:
        details_json = json.dumps(details, ensure_ascii=False) if details else "{}"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO usage_logs (event_type, lang, is_mock, details, user_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_type, lang, 1 if is_mock else 0, details_json, user_id),
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
    user_id: Optional[int] = None,
) -> int:
    """Save a generated product card to the database for history with optional user_id."""
    try:
        hashtags_json = json.dumps(hashtags, ensure_ascii=False) if isinstance(hashtags, list) else (hashtags or "[]")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO generated_cards (
                    title, description, price_tag, hashtags, marketing_tip,
                    studio_photo_url, photoshoot_style, content_tone, content_format,
                    cost_price, desired_price, note, lang, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title, description, price_tag, hashtags_json, marketing_tip,
                    studio_photo_url, photoshoot_style, content_tone, content_format,
                    cost_price, desired_price, note, lang, user_id
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
    user_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Retrieve generated product cards with search, favorites filtering, user isolation, and pagination."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT id, created_at, title, description, price_tag, hashtags,
                       marketing_tip, studio_photo_url, photoshoot_style,
                       content_tone, content_format, cost_price, desired_price,
                       note, lang, is_favorite, user_id
                FROM generated_cards
                WHERE 1=1
            """
            params: list[Any] = []
            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)
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
                    "has_studio_photo": bool(row["studio_photo_url"]),
                    "studio_photo_url": f"/api/cards/{row['id']}/photo" if (row["studio_photo_url"] and row["studio_photo_url"].startswith("data:")) else row["studio_photo_url"],
                    "photoshoot_style": row["photoshoot_style"],
                    "content_tone": row["content_tone"],
                    "content_format": row["content_format"],
                    "cost_price": row["cost_price"],
                    "desired_price": row["desired_price"],
                    "note": row["note"],
                    "lang": row["lang"],
                    "is_favorite": bool(row["is_favorite"]),
                    "user_id": row["user_id"],
                })
            return items
    except Exception as exc:
        logger.error("Failed to fetch history: %s", exc)
        return []


def get_history_count(favorites_only: bool = False, search: str = "", user_id: Optional[int] = None) -> int:
    """Get total count of generated cards matching filters."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as total FROM generated_cards WHERE 1=1"
            params: list[Any] = []
            if user_id is not None:
                query += " AND user_id = ?"
                params.append(user_id)
            if favorites_only:
                query += " AND is_favorite = 1"
            if search.strip():
                query += " AND (title LIKE ? OR description LIKE ? OR note LIKE ? OR hashtags LIKE ?)"
                kw = f"%{search.strip()}%"
                params.extend([kw, kw, kw, kw])
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row["total"] if row else 0
    except Exception as exc:
        logger.error("Failed to fetch history count: %s", exc)
        return 0


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
                INSERT INTO bot_subscribers (chat_id, username, lang, is_active, user_id)
                VALUES (?, ?, ?, 1, (SELECT user_id FROM users WHERE tg_id = ?))
                ON CONFLICT(chat_id) DO UPDATE SET 
                    is_active = 1, 
                    lang = excluded.lang, 
                    username = excluded.username,
                    user_id = COALESCE(excluded.user_id, bot_subscribers.user_id)
                """,
                (chat_id, username, lang, chat_id),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save subscriber: %s", exc)
        return False


def unsubscribe_subscriber(chat_id: int) -> bool:
    """Unsubscribe a Telegram user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE bot_subscribers SET is_active = 0 WHERE chat_id = ?",
                (chat_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to unsubscribe user %s: %s", chat_id, exc)
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


# ===========================================================================
# User Management & Admin Analytics Layer
# ===========================================================================

def upsert_user(
    tg_id: int,
    tg_username: str = "",
    tg_first_name: str = "",
    name: str = "",
    status: str = "self_employed",
    category: str = "sewing",
    sales_channel: str = "uzum",
    lang: str = "uz",
) -> Dict[str, Any]:
    """Create or update user on authentication."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
            existing = cursor.fetchone()
            if existing:
                # Do NOT silently re-activate an account that an administrator blocked (is_active == 0)
                update_fields = ["last_seen_at = CURRENT_TIMESTAMP"]
                params: List[Any] = []
                if tg_username:
                    update_fields.append("tg_username = ?")
                    params.append(tg_username)
                if tg_first_name:
                    update_fields.append("tg_first_name = ?")
                    params.append(tg_first_name)
                # Allow user to update their name if provided and not just placeholder
                if name and name.strip() and (not existing["name"] or existing["name"] in ("Tadbirkor", "Предпринимательница") or name.strip() != existing["name"]):
                    update_fields.append("name = ?")
                    params.append(name.strip())
                # Check if configured as admin in environment
                admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
                if admin_ids_str:
                    admin_ids = [i.strip() for i in admin_ids_str.split(",") if i.strip()]
                    if str(tg_id) in admin_ids and not existing.get("is_admin"):
                        update_fields.append("is_admin = 1")

                params.append(existing["user_id"])
                cursor.execute(
                    f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?",
                    tuple(params),
                )
                # Ensure bot_subscribers are linked to this user_id
                cursor.execute(
                    "UPDATE bot_subscribers SET user_id = ? WHERE chat_id = ? AND (user_id IS NULL OR user_id = 0)",
                    (existing["user_id"], tg_id),
                )
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (existing["user_id"],))
                row = cursor.fetchone()
                return dict(row) if row else dict(existing)
            else:
                display_name = name.strip() if name and name.strip() else (tg_first_name or "Tadbirkor")
                admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
                is_admin_flag = 0
                if admin_ids_str:
                    admin_ids = [i.strip() for i in admin_ids_str.split(",") if i.strip()]
                    if str(tg_id) in admin_ids:
                        is_admin_flag = 1

                cursor.execute(
                    """
                    INSERT INTO users (tg_id, tg_username, tg_first_name, name, status, category, sales_channel, lang, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tg_id, tg_username, tg_first_name, display_name, status, category, sales_channel, lang, is_admin_flag),
                )
                conn.commit()
                new_id = cursor.lastrowid
                # Link any existing bot subscription with this tg_id
                cursor.execute(
                    "UPDATE bot_subscribers SET user_id = ? WHERE chat_id = ? AND (user_id IS NULL OR user_id = 0)",
                    (new_id, tg_id),
                )
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (new_id,))
                return dict(cursor.fetchone())
    except Exception as exc:
        logger.error("Failed to upsert user: %s", exc)
        return {
            "user_id": 0,
            "tg_id": tg_id,
            "tg_username": tg_username,
            "tg_first_name": tg_first_name,
            "name": name or tg_first_name or "Tadbirkor",
            "status": status,
            "category": category,
            "sales_channel": sales_channel,
            "lang": lang,
        }


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get single user by user_id with extra stats."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            user_dict = dict(row)
            cursor.execute("SELECT COUNT(*) as cnt FROM generated_cards WHERE user_id = ?", (user_id,))
            user_dict["cards_count"] = cursor.fetchone()["cnt"]
            cursor.execute("SELECT is_active FROM bot_subscribers WHERE chat_id = ? OR user_id = ?", (user_dict.get("tg_id"), user_id))
            sub = cursor.fetchone()
            user_dict["is_subscriber"] = bool(sub["is_active"]) if sub else False
            user_dict["is_admin"] = bool(user_dict.get("is_admin", 0))
            return user_dict
    except Exception as exc:
        logger.error("Failed to get user %s: %s", user_id, exc)
        return None


def get_user_by_tg_id(tg_id: int) -> Optional[Dict[str, Any]]:
    """Get user by Telegram user ID."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
            row = cursor.fetchone()
            if not row:
                return None
            user_dict = dict(row)
            cursor.execute("SELECT COUNT(*) as cnt FROM generated_cards WHERE user_id = ?", (user_dict["user_id"],))
            user_dict["cards_count"] = cursor.fetchone()["cnt"]
            cursor.execute("SELECT is_active FROM bot_subscribers WHERE chat_id = ?", (tg_id,))
            sub = cursor.fetchone()
            user_dict["is_subscriber"] = bool(sub["is_active"]) if sub else False
            user_dict["is_admin"] = bool(user_dict.get("is_admin", 0))
            return user_dict
    except Exception as exc:
        logger.error("Failed to get user by tg_id %s: %s", tg_id, exc)
        return None


def set_user_admin(tg_id: int, is_admin: bool = True) -> bool:
    """Set or revoke administrator status in users table for given tg_id."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_admin = ? WHERE tg_id = ?", (1 if is_admin else 0, tg_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to set user admin for %s: %s", tg_id, exc)
        return False


def set_user_terms_agreed(tg_id: int, agreed: bool = True, lang: Optional[str] = None) -> bool:
    """Record user consent to terms of service and update their language if provided."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if lang:
                cursor.execute(
                    "UPDATE users SET agreed_terms = ?, lang = ?, last_seen_at = CURRENT_TIMESTAMP WHERE tg_id = ?",
                    (1 if agreed else 0, lang, tg_id),
                )
            else:
                cursor.execute(
                    "UPDATE users SET agreed_terms = ?, last_seen_at = CURRENT_TIMESTAMP WHERE tg_id = ?",
                    (1 if agreed else 0, tg_id),
                )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to set agreed terms for tg_id %s: %s", tg_id, exc)
        return False


def get_user_terms_agreed(tg_id: int) -> bool:
    """Check if user has agreed to terms of service."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT agreed_terms FROM users WHERE tg_id = ?", (tg_id,))
            row = cursor.fetchone()
            if not row or row["agreed_terms"] is None:
                return False
            return bool(row["agreed_terms"])
    except Exception as exc:
        logger.error("Failed to get terms agreed for tg_id %s: %s", tg_id, exc)
        return False


def set_user_lang(tg_id: int, lang: str) -> bool:
    """Update language preference for user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET lang = ?, last_seen_at = CURRENT_TIMESTAMP WHERE tg_id = ?",
                (lang, tg_id),
            )
            # Also sync with bot_subscribers if present
            cursor.execute(
                "UPDATE bot_subscribers SET lang = ? WHERE chat_id = ?",
                (lang, tg_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to set lang for tg_id %s: %s", tg_id, exc)
        return False


def get_user_lang(tg_id: int, default: str = "uz") -> str:
    """Get preferred language for user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lang FROM users WHERE tg_id = ?", (tg_id,))
            row = cursor.fetchone()
            if row and row["lang"]:
                return str(row["lang"])
            # Fallback to bot_subscribers
            cursor.execute("SELECT lang FROM bot_subscribers WHERE chat_id = ?", (tg_id,))
            sub_row = cursor.fetchone()
            if sub_row and sub_row["lang"]:
                return str(sub_row["lang"])
            return default
    except Exception as exc:
        logger.error("Failed to get lang for tg_id %s: %s", tg_id, exc)
        return default


def update_user_profile(
    user_id: int,
    name: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    sales_channel: Optional[str] = None,
    lang: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update profile fields for a user."""
    try:
        fields = ["last_seen_at = CURRENT_TIMESTAMP"]
        params: List[Any] = []
        if name is not None:
            fields.append("name = ?")
            params.append(name.strip())
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if category is not None:
            fields.append("category = ?")
            params.append(category)
        if sales_channel is not None:
            fields.append("sales_channel = ?")
            params.append(sales_channel)
        if lang is not None:
            fields.append("lang = ?")
            params.append(lang)

        params.append(user_id)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?", tuple(params))
            conn.commit()
        return get_user(user_id)
    except Exception as exc:
        logger.error("Failed to update user profile %s: %s", user_id, exc)
        return None


def get_all_users(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    status: str = "",
    category: str = "",
) -> List[Dict[str, Any]]:
    """Retrieve users list for admin with pagination, search, and filtering."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT u.*,
                       COALESCE((SELECT COUNT(*) FROM generated_cards c WHERE c.user_id = u.user_id), 0) AS cards_count,
                       COALESCE((SELECT is_active FROM bot_subscribers b WHERE b.chat_id = u.tg_id OR b.user_id = u.user_id LIMIT 1), 0) AS is_subscriber
                FROM users u
                WHERE 1=1
            """
            params: List[Any] = []
            if search.strip():
                kw = f"%{search.strip()}%"
                query += " AND (u.name LIKE ? OR u.tg_username LIKE ? OR u.tg_first_name LIKE ? OR CAST(u.tg_id AS TEXT) LIKE ?)"
                params.extend([kw, kw, kw, kw])
            if status.strip():
                query += " AND u.status = ?"
                params.append(status.strip())
            if category.strip():
                query += " AND u.category = ?"
                params.append(category.strip())

            query += " ORDER BY u.last_seen_at DESC, u.user_id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            return [dict(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.error("Failed to get all users: %s", exc)
        return []


def get_users_count(
    search: str = "",
    status: str = "",
    category: str = "",
) -> int:
    """Total users matching filter criteria."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as total FROM users WHERE 1=1"
            params: List[Any] = []
            if search.strip():
                kw = f"%{search.strip()}%"
                query += " AND (name LIKE ? OR tg_username LIKE ? OR tg_first_name LIKE ? OR CAST(tg_id AS TEXT) LIKE ?)"
                params.extend([kw, kw, kw, kw])
            if status.strip():
                query += " AND status = ?"
                params.append(status.strip())
            if category.strip():
                query += " AND category = ?"
                params.append(category.strip())

            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row["total"] if row else 0
    except Exception as exc:
        logger.error("Failed to get users count: %s", exc)
        return 0


def toggle_user_active(user_id: int) -> Optional[bool]:
    """Toggle is_active flag for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT is_active FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            new_val = 0 if row["is_active"] else 1
            cursor.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (new_val, user_id))
            conn.commit()
            return bool(new_val)
    except Exception as exc:
        logger.error("Failed to toggle user active status %s: %s", user_id, exc)
        return None


def get_admin_dashboard_metrics() -> Dict[str, Any]:
    """Aggregated statistics for Admin Dashboard."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total_users = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM users WHERE last_seen_at >= date('now', 'start of day')")
            active_today = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM users WHERE created_at >= date('now', '-7 days')")
            new_this_week = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM generated_cards")
            total_cards = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM bot_subscribers WHERE is_active = 1")
            total_subscribers = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as total FROM usage_logs")
            total_events = cursor.fetchone()["total"]

            cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM users 
                WHERE category IS NOT NULL AND category != ''
                GROUP BY category 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_categories = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM users 
                WHERE status IS NOT NULL AND status != ''
                GROUP BY status 
                ORDER BY count DESC
            """)
            top_statuses = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT sales_channel, COUNT(*) as count 
                FROM users 
                WHERE sales_channel IS NOT NULL AND sales_channel != ''
                GROUP BY sales_channel 
                ORDER BY count DESC
            """)
            top_channels = [dict(r) for r in cursor.fetchall()]

            cursor.execute("""
                WITH RECURSIVE dates(date) AS (
                    VALUES(date('now', '-6 days'))
                    UNION ALL
                    SELECT date(date, '+1 day')
                    FROM dates
                    WHERE date < date('now')
                )
                SELECT 
                    d.date,
                    COALESCE((SELECT COUNT(*) FROM users u WHERE date(u.created_at) = d.date), 0) AS new_users,
                    COALESCE((SELECT COUNT(*) FROM generated_cards c WHERE date(c.created_at) = d.date), 0) AS cards,
                    COALESCE((SELECT COUNT(*) FROM usage_logs l WHERE date(l.created_at) = d.date), 0) AS events
                FROM dates d
                ORDER BY d.date ASC
            """)
            daily_chart = [dict(r) for r in cursor.fetchall()]

            return {
                "total_users": total_users,
                "active_today": active_today,
                "new_this_week": new_this_week,
                "total_cards": total_cards,
                "total_subscribers": total_subscribers,
                "total_events": total_events,
                "top_categories": top_categories,
                "top_statuses": top_statuses,
                "top_channels": top_channels,
                "daily_activity": daily_chart,
            }
    except Exception as exc:
        logger.error("Failed to generate admin dashboard metrics: %s", exc)
        return {
            "total_users": 0,
            "active_today": 0,
            "new_this_week": 0,
            "total_cards": 0,
            "total_subscribers": 0,
            "total_events": 0,
            "top_categories": [],
            "top_statuses": [],
            "top_channels": [],
            "daily_activity": [],
        }


def get_admin_events(
    user_id: Optional[int] = None,
    event_type: str = "",
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve usage_logs for admin panel."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT l.*, u.name as user_name, u.tg_username
                FROM usage_logs l
                LEFT JOIN users u ON l.user_id = u.user_id
                WHERE 1=1
            """
            params: List[Any] = []
            if user_id:
                query += " AND l.user_id = ?"
                params.append(user_id)
            if event_type.strip():
                query += " AND l.event_type = ?"
                params.append(event_type.strip())
            
            query += " ORDER BY l.id DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            logs = []
            for row in cursor.fetchall():
                try:
                    d = json.loads(row["details"]) if row["details"] else {}
                except Exception:
                    d = {}
                logs.append({
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "event_type": row["event_type"],
                    "lang": row["lang"],
                    "is_mock": bool(row["is_mock"]),
                    "details": d,
                    "user_id": row["user_id"],
                    "user_name": row["user_name"],
                    "tg_username": row["tg_username"],
                })
            return logs
    except Exception as exc:
        logger.error("Failed to fetch admin events: %s", exc)
        return []


def get_admin_events_count(user_id: Optional[int] = None, event_type: str = "") -> int:
    """Count matching events."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as total FROM usage_logs WHERE 1=1"
            params: List[Any] = []
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if event_type.strip():
                query += " AND event_type = ?"
                params.append(event_type.strip())
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
            return row["total"] if row else 0
    except Exception as exc:
        logger.error("Failed to get admin events count: %s", exc)
        return 0


def get_admin_cards(
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Retrieve all cards across all users with user metadata."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT c.*, u.name as user_name, u.tg_username
                FROM generated_cards c
                LEFT JOIN users u ON c.user_id = u.user_id
                WHERE 1=1
            """
            params: List[Any] = []
            if user_id:
                query += " AND c.user_id = ?"
                params.append(user_id)
            query += " ORDER BY c.id DESC LIMIT ? OFFSET ?"
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
                    "has_studio_photo": bool(row["studio_photo_url"]),
                    "studio_photo_url": f"/api/cards/{row['id']}/photo" if (row["studio_photo_url"] and row["studio_photo_url"].startswith("data:")) else row["studio_photo_url"],
                    "photoshoot_style": row["photoshoot_style"],
                    "cost_price": row["cost_price"],
                    "desired_price": row["desired_price"],
                    "lang": row["lang"],
                    "is_favorite": bool(row["is_favorite"]),
                    "user_id": row["user_id"],
                    "user_name": row["user_name"],
                    "tg_username": row["tg_username"],
                })
            return items
    except Exception as exc:
        logger.error("Failed to get admin cards: %s", exc)
        return []


# ===========================================================================
# Uzum Market Data Access Layer (Multi-Shop, Orders, Stocks, Notifications)
# ===========================================================================

def get_uzum_settings() -> Dict[str, Any]:
    """Retrieve current Uzum API integration settings."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM uzum_settings WHERE id = 1")
            row = cursor.fetchone()
            if row:
                d = dict(row)
                # Mask API key if present
                raw_key = d.get("api_key") or ""
                if raw_key and len(raw_key) > 8:
                    d["masked_key"] = raw_key[:4] + "••••••••" + raw_key[-4:]
                else:
                    d["masked_key"] = raw_key
                return d
    except Exception as exc:
        logger.error("Failed to get uzum settings: %s", exc)
    return {
        "id": 1,
        "api_key": "",
        "masked_key": "",
        "is_connected": 0,
        "is_demo": 0,
        "notifications_enabled": 1,
        "low_stock_threshold": 3,
        "telegram_chat_id": None,
        "last_sync_at": None,
    }


def save_uzum_settings(
    api_key: Optional[str] = None,
    is_connected: Optional[int] = None,
    is_demo: Optional[int] = None,
    notifications_enabled: Optional[int] = None,
    low_stock_threshold: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
    last_sync_at: Optional[str] = None,
) -> bool:
    """Update Uzum integration settings."""
    try:
        current = get_uzum_settings()
        new_key = api_key if api_key is not None else current.get("api_key")
        new_connected = is_connected if is_connected is not None else current.get("is_connected", 0)
        new_demo = is_demo if is_demo is not None else current.get("is_demo", 0)
        new_notify = notifications_enabled if notifications_enabled is not None else current.get("notifications_enabled", 1)
        new_thresh = low_stock_threshold if low_stock_threshold is not None else current.get("low_stock_threshold", 3)
        new_chat_id = telegram_chat_id if telegram_chat_id is not None else current.get("telegram_chat_id")
        new_sync = last_sync_at if last_sync_at is not None else current.get("last_sync_at")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE uzum_settings
                SET api_key = ?, is_connected = ?, is_demo = ?, notifications_enabled = ?,
                    low_stock_threshold = ?, telegram_chat_id = ?, last_sync_at = ?
                WHERE id = 1
                """,
                (new_key, new_connected, new_demo, new_notify, new_thresh, new_chat_id, new_sync),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save uzum settings: %s", exc)
        return False


def get_uzum_shops() -> List[Dict[str, Any]]:
    """Retrieve all seller shops belonging to the connected account."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*,
                       COALESCE((
                           SELECT COUNT(*)
                           FROM uzum_orders o
                           WHERE o.shop_id = s.shop_id AND o.status IN ('CREATED', 'PENDING')
                       ), 0) AS pending_orders_count
                FROM uzum_shops s
                ORDER BY s.shop_id ASC
            """)
            return [dict(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.error("Failed to get uzum shops: %s", exc)
        return []


def save_uzum_shops(shops: List[Dict[str, Any]]) -> bool:
    """Save or update list of shops from Uzum API."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for s in shops:
                cursor.execute(
                    """
                    INSERT INTO uzum_shops (shop_id, title, legal_name, inn, status, is_selected, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(shop_id) DO UPDATE SET
                        title = excluded.title,
                        legal_name = excluded.legal_name,
                        inn = excluded.inn,
                        status = excluded.status,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        s["shop_id"],
                        s["title"],
                        s.get("legal_name", ""),
                        s.get("inn", ""),
                        s.get("status", "ACTIVE"),
                        s.get("is_selected", 0),
                    ),
                )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save uzum shops: %s", exc)
        return False


def get_uzum_orders(
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Retrieve orders with filtering by shop_id and status, including nested items."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM uzum_orders WHERE 1=1"
            params: List[Any] = []
            if shop_id and shop_id != 0:
                query += " AND shop_id = ?"
                params.append(shop_id)
            if status and status != "ALL":
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            orders = [dict(r) for r in cursor.fetchall()]

            # Fetch items for each order
            for o in orders:
                cursor.execute(
                    "SELECT * FROM uzum_order_items WHERE order_id = ? ORDER BY id ASC",
                    (o["order_id"],),
                )
                o["items"] = [dict(item) for item in cursor.fetchall()]
            return orders
    except Exception as exc:
        logger.error("Failed to get uzum orders: %s", exc)
        return []


def save_uzum_orders(orders: List[Dict[str, Any]]) -> bool:
    """Save or update Uzum orders and their items."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for o in orders:
                cursor.execute(
                    """
                    INSERT INTO uzum_orders (
                        order_id, shop_id, shop_title, posting_number, status,
                        status_label_ru, status_label_uz, total_amount, delivery_type,
                        customer_name, delivery_city, created_at, deadline_to_confirm,
                        is_notified, raw_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(order_id) DO UPDATE SET
                        status = excluded.status,
                        status_label_ru = excluded.status_label_ru,
                        status_label_uz = excluded.status_label_uz,
                        total_amount = excluded.total_amount,
                        deadline_to_confirm = excluded.deadline_to_confirm
                    """,
                    (
                        o["order_id"],
                        o["shop_id"],
                        o.get("shop_title", ""),
                        o.get("posting_number", str(o["order_id"])),
                        o["status"],
                        o.get("status_label_ru", o["status"]),
                        o.get("status_label_uz", o["status"]),
                        float(o.get("total_amount", 0)),
                        o.get("delivery_type", "FBS"),
                        o.get("customer_name", "Xaridor"),
                        o.get("delivery_city", "Toshkent"),
                        o.get("created_at", datetime.now().isoformat()),
                        o.get("deadline_to_confirm"),
                        o.get("is_notified", 0),
                        json.dumps(o.get("raw_json", {}), ensure_ascii=False),
                    ),
                )
                # Insert items if provided
                if "items" in o and isinstance(o["items"], list):
                    for item in o["items"]:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO uzum_order_items (
                                order_id, sku_id, product_title, quantity, price, barcode
                            )
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                o["order_id"],
                                item["sku_id"],
                                item["product_title"],
                                int(item.get("quantity", 1)),
                                float(item.get("price", 0)),
                                item.get("barcode", ""),
                            ),
                        )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save uzum orders: %s", exc)
        return False


def update_uzum_order_status(
    order_id: int,
    new_status: str,
    status_label_ru: Optional[str] = None,
    status_label_uz: Optional[str] = None,
) -> bool:
    """Update order status (e.g. after confirming or cancelling)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE uzum_orders
                SET status = ?,
                    status_label_ru = COALESCE(?, status_label_ru),
                    status_label_uz = COALESCE(?, status_label_uz)
                WHERE order_id = ?
                """,
                (new_status, status_label_ru, status_label_uz, order_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to update order status: %s", exc)
        return False


def get_unnotified_uzum_orders() -> List[Dict[str, Any]]:
    """Retrieve all pending orders that have not yet sent a Telegram push notification."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM uzum_orders WHERE is_notified = 0 AND status IN ('CREATED', 'PENDING') ORDER BY created_at ASC"
            )
            orders = [dict(r) for r in cursor.fetchall()]
            for o in orders:
                cursor.execute(
                    "SELECT * FROM uzum_order_items WHERE order_id = ?",
                    (o["order_id"],),
                )
                o["items"] = [dict(item) for item in cursor.fetchall()]
            return orders
    except Exception as exc:
        logger.error("Failed to get unnotified orders: %s", exc)
        return []


def mark_order_notified(order_id: int) -> bool:
    """Flag an order as having been notified in Telegram."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE uzum_orders SET is_notified = 1 WHERE order_id = ?",
                (order_id,),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to mark order notified: %s", exc)
        return False


def get_uzum_stocks(shop_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve SKU stock balances and prices."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if shop_id and shop_id != 0:
                cursor.execute(
                    "SELECT * FROM uzum_stocks WHERE shop_id = ? ORDER BY is_low_stock DESC, current_stock ASC",
                    (shop_id,),
                )
            else:
                cursor.execute(
                    "SELECT * FROM uzum_stocks ORDER BY is_low_stock DESC, current_stock ASC"
                )
            return [dict(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.error("Failed to get uzum stocks: %s", exc)
        return []


def save_uzum_stocks(stocks: List[Dict[str, Any]]) -> bool:
    """Upsert stock items with FBO/FBS stocks and cost prices."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            for s in stocks:
                is_low = 1 if int(s.get("current_stock", 0)) <= 3 else 0
                cost = float(s.get("cost_price", 0))
                fbo = int(s.get("fbo_stock", s.get("current_stock", 0)))
                velocity = float(s.get("daily_sales_velocity", 1.5))
                cursor.execute(
                    """
                    INSERT INTO uzum_stocks (
                        sku_id, shop_id, shop_title, product_title, barcode,
                        current_stock, price, is_low_stock, cost_price, fbo_stock, daily_sales_velocity, last_synced_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(sku_id) DO UPDATE SET
                        current_stock = excluded.current_stock,
                        price = excluded.price,
                        is_low_stock = excluded.is_low_stock,
                        cost_price = CASE WHEN excluded.cost_price > 0 THEN excluded.cost_price ELSE uzum_stocks.cost_price END,
                        fbo_stock = excluded.fbo_stock,
                        daily_sales_velocity = excluded.daily_sales_velocity,
                        last_synced_at = CURRENT_TIMESTAMP
                    """,
                    (
                        s["sku_id"],
                        s["shop_id"],
                        s.get("shop_title", ""),
                        s["product_title"],
                        s.get("barcode", ""),
                        int(s.get("current_stock", 0)),
                        float(s.get("price", 0)),
                        is_low,
                        cost,
                        fbo,
                        velocity,
                    ),
                )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to save uzum stocks: %s", exc)
        return False


def update_uzum_stock_amount(sku_id: int, new_amount: int) -> bool:
    """Update stock quantity for a single SKU."""
    try:
        is_low = 1 if new_amount <= 3 else 0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE uzum_stocks
                SET current_stock = ?, is_low_stock = ?, last_synced_at = CURRENT_TIMESTAMP
                WHERE sku_id = ?
                """,
                (new_amount, is_low, sku_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to update stock amount: %s", exc)
        return False


def update_uzum_price(sku_id: int, new_price: float) -> bool:
    """Update selling price for a single SKU."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE uzum_stocks
                SET price = ?, last_synced_at = CURRENT_TIMESTAMP
                WHERE sku_id = ?
                """,
                (new_price, sku_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to update stock price: %s", exc)
        return False


def update_uzum_cost_price(sku_id: int, cost_price: float) -> bool:
    """Update prime cost (tannarx) for a SKU to calculate net profit and margins accurately."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE uzum_stocks
                SET cost_price = ?, last_synced_at = CURRENT_TIMESTAMP
                WHERE sku_id = ?
                """,
                (cost_price, sku_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    except Exception as exc:
        logger.error("Failed to update cost price: %s", exc)
        return False


def get_uzum_margin_analytics(shop_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Calculate unit economics and margin health for all SKUs:
    - Uzum commission (avg 13%)
    - Logistics fee (12,000 UZS)
    - 1% YaTT turnover tax
    - Prime cost
    - Net profit and margin %
    - Healthy (>=25%), Tight (10-24%), Danger (<10%)
    """
    try:
        stocks = get_uzum_stocks(shop_id=shop_id)
        analyzed_items = []
        healthy_cnt = 0
        tight_cnt = 0
        danger_cnt = 0

        for s in stocks:
            price = float(s.get("price", 0))
            cost = float(s.get("cost_price", 0))
            # Fallback cost estimate to 50% if unconfigured
            if cost <= 0:
                cost = round(price * 0.5)

            uzum_fee = round(price * 0.13)
            logistics = 12000.0
            tax_1pct = round(price * 0.01)
            total_deductions = cost + uzum_fee + logistics + tax_1pct
            net_profit = round(price - total_deductions)
            margin_pct = round((net_profit / max(1.0, price)) * 100, 1)

            # Recommended break-even + profit price
            # price * (1 - 0.14) >= cost + 12000 + 25000 (target profit 25k)
            target_profit = max(20000.0, price * 0.2)
            recommended_price = round((cost + logistics + target_profit) / 0.86, -3)

            if margin_pct >= 25:
                status = "HEALTHY"
                status_ru = "Высокая прибыль"
                status_uz = "Yuqori foyda"
                healthy_cnt += 1
            elif margin_pct >= 10:
                status = "TIGHT"
                status_ru = "Умеренная маржа"
                status_uz = "O'rtacha marja"
                tight_cnt += 1
            else:
                status = "DANGER"
                status_ru = "Опасность убытка!"
                status_uz = "Zarar xavfi!"
                danger_cnt += 1

            analyzed_items.append({
                "sku_id": s["sku_id"],
                "shop_id": s["shop_id"],
                "shop_title": s.get("shop_title", ""),
                "product_title": s["product_title"],
                "price": price,
                "cost_price": cost,
                "uzum_fee": uzum_fee,
                "logistics": logistics,
                "tax_1pct": tax_1pct,
                "net_profit": net_profit,
                "margin_pct": margin_pct,
                "recommended_price": recommended_price,
                "status": status,
                "status_ru": status_ru,
                "status_uz": status_uz,
            })

        avg_margin = round(sum(i["margin_pct"] for i in analyzed_items) / max(1, len(analyzed_items)), 1)
        return {
            "items": analyzed_items,
            "total_items": len(analyzed_items),
            "healthy_count": healthy_cnt,
            "tight_count": tight_cnt,
            "danger_count": danger_cnt,
            "avg_margin_pct": avg_margin,
        }
    except Exception as exc:
        logger.error("Failed to calculate margin analytics: %s", exc)
        return {
            "items": [],
            "total_items": 0,
            "healthy_count": 0,
            "tight_count": 0,
            "danger_count": 0,
            "avg_margin_pct": 0,
        }


def get_uzum_fbo_forecast(shop_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Calculate restock forecast for FBO inventory:
    - Current FBO warehouse stock
    - Daily sales rate
    - Days of stock remaining
    - Urgency: CRITICAL (<= 3d), WARNING (4-7d), OPTIMAL (> 7d)
    - Recommended reorder batch size
    """
    try:
        stocks = get_uzum_stocks(shop_id=shop_id)
        forecasts = []
        for s in stocks:
            fbo_stock = int(s.get("fbo_stock", s.get("current_stock", 0)))
            velocity = float(s.get("daily_sales_velocity", 1.5))
            if velocity <= 0:
                velocity = 1.0

            days_remaining = round(fbo_stock / velocity, 1)
            recommended_reorder = int(max(10, round(velocity * 14)))  # 2 weeks buffer

            if days_remaining <= 3.0:
                urgency = "CRITICAL"
                urgency_ru = "Срочно пополнить!"
                urgency_uz = "Zudlik bilan yetkazing!"
                tip_ru = f"Остатка на складе Uzum хватит всего на {days_remaining:.0f} дн. Создайте поставку на {recommended_reorder} шт. до четверга!"
                tip_uz = f"Uzum omboridagi qoldiq atigi {days_remaining:.0f} kunga yetadi. Payshanbagacha {recommended_reorder} dona yangi partiya topshiring!"
            elif days_remaining <= 7.0:
                urgency = "WARNING"
                urgency_ru = "Пополнить на этой неделе"
                urgency_uz = "Shu hafta yetkazing"
                tip_ru = f"Запас на {days_remaining:.0f} дн. Рекомендуется подготовить поставку на {recommended_reorder} шт."
                tip_uz = f"Zaxira {days_remaining:.0f} kunga yetadi. {recommended_reorder} dona mahsulot yetkazib berish tavsiya etiladi."
            else:
                urgency = "OPTIMAL"
                urgency_ru = "Запас достаточный"
                urgency_uz = "Zaxira yetarli"
                tip_ru = f"Запас на {days_remaining:.0f} дн. Товар хорошо обеспечен."
                tip_uz = f"Zaxira {days_remaining:.0f} kunga yetarli."

            forecasts.append({
                "sku_id": s["sku_id"],
                "shop_id": s["shop_id"],
                "shop_title": s.get("shop_title", ""),
                "product_title": s["product_title"],
                "fbo_stock": fbo_stock,
                "daily_sales_velocity": velocity,
                "days_remaining": days_remaining,
                "recommended_reorder": recommended_reorder,
                "urgency": urgency,
                "urgency_ru": urgency_ru,
                "urgency_uz": urgency_uz,
                "tip_ru": tip_ru,
                "tip_uz": tip_uz,
            })

        # Sort with most critical first
        forecasts.sort(key=lambda x: x["days_remaining"])
        return forecasts
    except Exception as exc:
        logger.error("Failed to get FBO forecast: %s", exc)
        return []


def get_uzum_finance_summary(shop_id: Optional[int] = None) -> Dict[str, Any]:
    """Calculate consolidated or shop-specific revenue, commission, and net payout."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT SUM(total_amount) as gross, COUNT(*) as cnt FROM uzum_orders WHERE status NOT IN ('CANCELLED')"
            params: List[Any] = []
            if shop_id and shop_id != 0:
                query += " AND shop_id = ?"
                params.append(shop_id)

            cursor.execute(query, params)
            row = cursor.fetchone()
            gross = float(row["gross"] or 0) if row else 0.0
            order_count = int(row["cnt"] or 0) if row else 0

            # Commission approx: 14% on average in Uzum
            commission_rate = 0.14
            commission_amount = round(gross * commission_rate)
            # Logistics fee approx: 5 250 UZS per order
            logistics_fee = order_count * 5250
            # 1% turnover tax withheld by Uzum as tax agent
            tax_turnover = round(gross * 0.01)
            # Net payout
            net_payout = max(0.0, gross - commission_amount - logistics_fee - tax_turnover)

            return {
                "gross_revenue": gross,
                "order_count": order_count,
                "commission_rate": commission_rate,
                "commission_amount": commission_amount,
                "logistics_fee": logistics_fee,
                "tax_turnover": tax_turnover,
                "net_payout": net_payout,
            }
    except Exception as exc:
        logger.error("Failed to get uzum finance summary: %s", exc)
        return {
            "gross_revenue": 0.0,
            "order_count": 0,
            "commission_rate": 0.14,
            "commission_amount": 0.0,
            "logistics_fee": 0.0,
            "tax_turnover": 0.0,
            "net_payout": 0.0,
        }


def log_uzum_notification(
    event_type: str,
    message: str,
    sent_to_chat_id: int,
    shop_id: Optional[int] = None,
    order_id: Optional[int] = None,
    status: str = "sent",
) -> bool:
    """Log an outgoing push notification."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO uzum_notifications_log (
                    event_type, shop_id, order_id, message, sent_to_chat_id, status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event_type, shop_id, order_id, message, sent_to_chat_id, status),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to log uzum notification: %s", exc)
        return False


def reset_uzum_data() -> bool:
    """Reset all Uzum local tables for fresh sync."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM uzum_order_items")
            cursor.execute("DELETE FROM uzum_orders")
            cursor.execute("DELETE FROM uzum_stocks")
            cursor.execute("DELETE FROM uzum_shops")
            cursor.execute("DELETE FROM uzum_notifications_log")
            cursor.execute("UPDATE uzum_settings SET is_connected = 0, is_demo = 0, last_sync_at = NULL WHERE id = 1")
            conn.commit()
            return True
    except Exception as exc:
        logger.error("Failed to reset uzum data: %s", exc)
        return False


# Auto-initialize on module load
init_db()
