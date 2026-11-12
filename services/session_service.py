"""
session_service.py — Signed session tokens and server secrets.

After a successful login the server issues a session token bound to the internal user_id.
Every user-scoped API endpoint derives the user from this token, never from a client-supplied
user_id, so one user cannot read or modify another user's data.

Token format: base64url(json payload) + "." + base64url(HMAC-SHA256(payload, SESSION_SECRET)).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("oqila_session")

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", str(30 * 24 * 3600)))
MIN_ADMIN_KEY_LENGTH = 16

_ephemeral_secret: Optional[str] = None


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


SECRET_FILE = Path(os.getenv("SESSION_SECRET_FILE") or (Path(__file__).parent.parent / ".session_secret"))


def _load_or_create_secret_file() -> Optional[str]:
    """Read the generated secret shared by all workers, creating it (mode 0600) on first use."""
    try:
        fd = os.open(str(SECRET_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        # Another worker may have created the file a moment ago and still be writing it
        for _ in range(20):
            try:
                value = SECRET_FILE.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            if value:
                return value
            time.sleep(0.05)
        return None
    except OSError:
        return None
    value = secrets.token_urlsafe(48)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(value)
    logger.warning("SESSION_SECRET is not set: generated one in %s", SECRET_FILE)
    return value


def get_session_secret() -> bytes:
    """Secret used to sign session tokens.

    Uses SESSION_SECRET when configured. Otherwise a generated secret stored in .session_secret
    (shared by all uvicorn workers, kept across restarts). If the file cannot be written, a random
    per-process secret is used as a last resort.
    """
    global _ephemeral_secret
    configured = os.getenv("SESSION_SECRET", "").strip()
    if configured:
        return configured.encode("utf-8")
    if _ephemeral_secret is None:
        _ephemeral_secret = _load_or_create_secret_file()
        if _ephemeral_secret is None:
            _ephemeral_secret = secrets.token_urlsafe(48)
            logger.warning("SESSION_SECRET is not set and %s is not writable: sessions reset on restart.", SECRET_FILE)
    return _ephemeral_secret.encode("utf-8")


def create_session_token(user_id: int, ttl_seconds: Optional[int] = None) -> str:
    payload = {"uid": int(user_id), "exp": int(time.time()) + int(ttl_seconds or SESSION_TTL_SECONDS)}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64e(hmac.new(get_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_session_token(token: Optional[str]) -> Optional[int]:
    """Return the user_id carried by a valid, unexpired token, else None."""
    if not token or not isinstance(token, str) or token.count(".") != 1:
        return None
    body, sig = token.split(".", 1)
    try:
        expected = _b64e(hmac.new(get_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            return None
        payload: Dict[str, Any] = json.loads(_b64d(body))
        if int(payload.get("exp", 0)) < time.time():
            return None
        uid = int(payload["uid"])
        return uid if uid > 0 else None
    except Exception:
        return None


MEDIA_TOKEN_TTL_SECONDS = 600


def create_media_token(user_id: int, ttl_seconds: int = MEDIA_TOKEN_TTL_SECONDS) -> str:
    """Short-lived token for URLs loaded by <img>/<a> tags (`?mt=`). Unlike the 30-day session token it may
    appear in a URL: it expires in 10 minutes and only opens the user's own media."""
    payload = {"uid": int(user_id), "exp": int(time.time()) + int(ttl_seconds), "aud": "media"}
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64e(hmac.new(get_session_secret(), b"media:" + body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_media_token(token: Optional[str]) -> Optional[int]:
    """Return the user_id of a valid, unexpired media token, else None. Session tokens are not accepted."""
    if not token or not isinstance(token, str) or token.count(".") != 1:
        return None
    body, sig = token.split(".", 1)
    try:
        expected = _b64e(hmac.new(get_session_secret(), b"media:" + body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, sig):
            return None
        payload: Dict[str, Any] = json.loads(_b64d(body))
        if payload.get("aud") != "media" or int(payload.get("exp", 0)) < time.time():
            return None
        uid = int(payload["uid"])
        return uid if uid > 0 else None
    except Exception:
        return None


def get_admin_secret_key() -> Optional[str]:
    """Configured administrator key, or None when it is missing or too short (admin access disabled)."""
    key = os.getenv("ADMIN_SECRET_KEY", "").strip()
    if len(key) < MIN_ADMIN_KEY_LENGTH:
        return None
    return key


def check_admin_key(provided: Optional[str]) -> bool:
    configured = get_admin_secret_key()
    if not configured or not provided:
        return False
    return hmac.compare_digest(provided.strip().encode("utf-8"), configured.encode("utf-8"))


def get_webhook_secret() -> Optional[str]:
    """Secret token Telegram must echo in X-Telegram-Bot-Api-Secret-Token.

    Uses TELEGRAM_WEBHOOK_SECRET when set, otherwise derives a stable one from the bot token,
    so webhook verification is always on when the bot is configured.
    """
    configured = os.getenv("TELEGRAM_WEBHOOK_SECRET", "").strip()
    if configured:
        return configured
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        return None
    # Telegram allows 1-256 chars of A-Z, a-z, 0-9, _ and -
    return hashlib.sha256(b"oqila-webhook:" + bot_token.encode("utf-8")).hexdigest()


def new_guest_tg_id() -> int:
    """Identity for a browser guest: a negative id can never collide with a real Telegram user id."""
    return -secrets.randbelow(2**53 - 1) - 1
