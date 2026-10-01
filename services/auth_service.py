"""
auth_service.py — Telegram WebApp initData validation and session resolution
Features:
- Validates HMAC-SHA256 signature of Telegram WebApp initData according to official specs
- Extracts authenticated user details (id, username, first_name, language_code)
- Provides safe development fallback when running in a standalone browser outside Telegram
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import urllib.parse
from typing import Any, Dict, Optional

logger = logging.getLogger("oqila_auth")


def verify_telegram_init_data(init_data: str, bot_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Verify the cryptographic signature of Telegram WebApp initData.
    Returns parsed user dict on success, None on validation failure.
    """
    if not init_data or not isinstance(init_data, str):
        return None

    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        # Sort all parameters alphabetically
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

        # Secret key: HMAC-SHA256 with key "WebAppData" and bot token as message
        secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            logger.warning("Telegram initData hash mismatch")
            return None

        user_raw = parsed.get("user")
        if user_raw:
            return json.loads(user_raw)
        return None
    except Exception as exc:
        logger.error("Failed to verify telegram initData: %s", exc)
        return None


def resolve_auth_user(init_data: Optional[str] = None, dev_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Resolve user data either from valid Telegram initData or safe browser fallback.
    """
    if init_data:
        verified_user = verify_telegram_init_data(init_data)
        if verified_user:
            return {
                "tg_id": verified_user.get("id"),
                "tg_username": verified_user.get("username", ""),
                "tg_first_name": verified_user.get("first_name", ""),
                "lang": verified_user.get("language_code", "uz") if verified_user.get("language_code") in ("uz", "ru") else "uz",
                "is_authenticated": True,
            }

    # Browser standalone fallback (e.g. testing in desktop browser outside Telegram)
    dev_name = (dev_profile or {}).get("name", "Tadbirkor")
    dev_lang = (dev_profile or {}).get("lang", "uz")
    dev_status = (dev_profile or {}).get("status", "self_employed")
    dev_category = (dev_profile or {}).get("category", "sewing")
    dev_channel = (dev_profile or {}).get("salesChannel", "uzum")

    return {
        "tg_id": None,
        "tg_username": "web_guest",
        "tg_first_name": dev_name,
        "name": dev_name,
        "status": dev_status,
        "category": dev_category,
        "sales_channel": dev_channel,
        "lang": dev_lang,
        "is_authenticated": False,
    }
