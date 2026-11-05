"""
media_storage.py — Card studio photos stored as files instead of base64 blobs in SQLite.

A data: URL produced by the AI photoshoot is decoded and written to MEDIA_DIR/cards/<random>.<ext>;
the database keeps only the reference "file:cards/<name>". Keeping megabytes of base64 out of
SQLite keeps the database small and history queries fast.
"""
from __future__ import annotations

import base64
import binascii
import logging
import os
import secrets
from pathlib import Path
from typing import Optional

logger = logging.getLogger("oqila_media")

FILE_PREFIX = "file:"
MAX_PHOTO_BYTES = 15 * 1024 * 1024
_EXT_BY_MIME = {"image/png": "png", "image/jpeg": "jpg", "image/jpg": "jpg", "image/webp": "webp"}
MIME_BY_EXT = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


def media_dir() -> Path:
    return Path(os.getenv("OQILA_MEDIA_DIR") or (Path(__file__).parent.parent / "media"))


def is_stored_file(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(FILE_PREFIX)


def is_served_photo(value: Optional[str]) -> bool:
    """True for photos served through /api/cards/{id}/photo (files and legacy inline data URLs)."""
    return bool(value) and (value.startswith(FILE_PREFIX) or value.startswith("data:"))


def store_photo(value: Optional[str]) -> Optional[str]:
    """Persist a data: URL as a file and return its "file:" reference.

    Other values (None, https:// URLs, existing references) are returned unchanged. If the data
    cannot be decoded or written, the original value is kept so no photo is lost.
    """
    if not value or not value.startswith("data:"):
        return value
    try:
        header, b64_data = value.split(",", 1)
        mime = header[5:].split(";", 1)[0].strip().lower()
        ext = _EXT_BY_MIME.get(mime)
        if not ext or ";base64" not in header:
            return value
        raw = base64.b64decode(b64_data, validate=False)
        if not raw or len(raw) > MAX_PHOTO_BYTES:
            return value
        folder = media_dir() / "cards"
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{secrets.token_hex(16)}.{ext}"
        (folder / name).write_bytes(raw)
        return f"{FILE_PREFIX}cards/{name}"
    except (ValueError, binascii.Error, OSError) as exc:
        logger.warning("Could not store photo as file, keeping inline data: %s", exc)
        return value


def resolve_photo(value: Optional[str]) -> Optional[Path]:
    """Absolute path of a stored photo, or None if missing or outside MEDIA_DIR."""
    if not is_stored_file(value):
        return None
    root = media_dir().resolve()
    path = (root / value[len(FILE_PREFIX):]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    return path


def delete_photo(value: Optional[str]) -> None:
    path = resolve_photo(value)
    if path:
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Could not delete photo %s: %s", path, exc)
