"""
secret_box.py — encryption of secrets kept in SQLite (the sellers' Uzum API keys).

A copy of the database file (a backup, a leaked dump) must not give away working marketplace keys.
Values are encrypted with Fernet (AES-128-CBC + HMAC). The key comes from UZUM_KEY_ENCRYPTION_KEY in .env
(generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
If the variable is missing, a key is generated once in `.uzum_key` next to the application (mode 0600), so
encryption is never silently off; keep that file out of database backups and do not lose it.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("oqila_secrets")

TOKEN_PREFIX = "gAAAA"  # every Fernet token starts with the version byte 0x80, i.e. "gAAAA" in base64
_generated_key: Optional[bytes] = None


def _key_file() -> Path:
    return Path(os.getenv("UZUM_KEY_FILE") or (Path(__file__).parent.parent / ".uzum_key"))


def _key() -> bytes:
    global _generated_key
    configured = os.getenv("UZUM_KEY_ENCRYPTION_KEY", "").strip()
    if configured:
        try:
            Fernet(configured.encode("ascii"))
            return configured.encode("ascii")
        except Exception:
            # Not a Fernet key: use it as a passphrase
            return base64.urlsafe_b64encode(hashlib.sha256(configured.encode("utf-8")).digest())
    if _generated_key is None:
        path = _key_file()
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            key = Fernet.generate_key()
            with os.fdopen(fd, "wb") as fh:
                fh.write(key)
            logger.warning("UZUM_KEY_ENCRYPTION_KEY is not set: generated a key in %s", path)
            _generated_key = key
        except FileExistsError:
            _generated_key = path.read_bytes().strip()
    return _generated_key


def is_encrypted(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(TOKEN_PREFIX)


def encrypt(value: Optional[str]) -> Optional[str]:
    """Encrypt a secret for storage; empty values and already encrypted ones are returned unchanged."""
    if not value or is_encrypted(value):
        return value
    return Fernet(_key()).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: Optional[str]) -> Optional[str]:
    """The stored secret in clear text. Legacy plain values pass through; an undecryptable one becomes ""."""
    if not value or not is_encrypted(value):
        return value
    try:
        return Fernet(_key()).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        logger.error("A stored secret cannot be decrypted (was UZUM_KEY_ENCRYPTION_KEY changed?)")
        return ""
