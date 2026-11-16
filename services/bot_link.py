"""The public link of the Telegram bot, from TELEGRAM_BOT_USERNAME (one place instead of copies in messages)."""
from __future__ import annotations

import os

DEFAULT_BOT = "oqila_ai_bot"


def bot_username() -> str:
    return os.getenv("TELEGRAM_BOT_USERNAME", DEFAULT_BOT).strip().lstrip("@") or DEFAULT_BOT


def bot_url() -> str:
    return f"https://t.me/{bot_username()}"
