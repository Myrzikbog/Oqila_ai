#!/usr/bin/env python3
"""
migrate_posters.py — one-off migration from server-drawn posters to ordinary pictures.

Before the unified AI pipeline a poster was not a picture: it was drawn on every request from a text config
(generated_cards.poster_config) over the AI scene or the seller's photo. The application no longer draws text,
so each such poster is "baked" once with the old renderer (scripts/legacy_poster.py) and stored as the card's
picture. Cards keep looking exactly as they did; their text moves to info_config (marked "legacy") so the seller
can re-draw them with the AI when they want.

  - poster_config, no info_config  -> bake, store as studio_photo_url, delete the old scene file,
                                      move the text to info_config, clear poster_config
  - poster_config and info_config  -> the card already has an AI picture: only clear poster_config
  - offline cards (no picture)     -> baked from the seller's own photo the same way

Idempotent: a migrated card has no poster_config, so a second run finds nothing to do.

Usage:  python scripts/migrate_posters.py [--dry-run]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _open(ref: Optional[str]):
    """A stored picture (file reference or legacy inline data URL) as a PIL image, or None."""
    from PIL import Image

    from services.media_storage import resolve_photo

    if not ref:
        return None
    try:
        path = resolve_photo(ref)
        if path:
            img = Image.open(path)
        elif ref.startswith("data:") and "," in ref:
            img = Image.open(io.BytesIO(base64.b64decode(ref.split(",", 1)[1])))
        else:
            return None
        img.load()
        return img
    except Exception as exc:
        print(f"  ! could not open {ref[:40]}: {exc}")
        return None


def legacy_copy(config: Dict[str, Any]) -> Dict[str, Any]:
    """The poster's text as a CopySpec dict marked legacy."""
    from services.info_photo import CopySpec

    copy = CopySpec.from_dict({
        "title": config.get("title"), "bullets": config.get("bullets"), "price": config.get("price"),
        "old_price": config.get("old_price"), "badge": config.get("badge_text"), "deadline": config.get("deadline"),
        "contact": config.get("contact"), "cta": config.get("cta"), "brand_name": config.get("brand_name"),
        "lang": config.get("lang"), "legacy": True,
    })
    return copy.to_dict()


def migrate(dry_run: bool = False) -> Dict[str, int]:
    from legacy_poster import PosterSpec, render_poster

    from services.database import get_db_connection, init_db
    from services.media_storage import delete_photo, store_bytes

    init_db()
    stats = {"baked": 0, "cleared": 0, "failed": 0}
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT c.id, c.user_id, c.studio_photo_url, c.source_photo_url, c.poster_config, c.info_config, u.brand_logo "
            "FROM generated_cards c LEFT JOIN users u ON u.user_id = c.user_id "
            "WHERE c.poster_config IS NOT NULL AND c.poster_config != ''"
        ).fetchall()
    rows = [dict(r) for r in rows]
    to_delete: List[str] = []
    for row in rows:
        if row["info_config"]:
            stats["cleared"] += 1
            if not dry_run:
                with get_db_connection() as conn:
                    conn.execute("UPDATE generated_cards SET poster_config = NULL WHERE id = ?", (row["id"],))
                    conn.commit()
            continue
        try:
            config = json.loads(row["poster_config"])
            spec = PosterSpec.from_dict(config)
            background = _open(row["studio_photo_url"])
            source = None if background is not None else _open(row["source_photo_url"])
            logo = _open(row["brand_logo"]) if spec.show_logo else None
            image = render_poster(spec, background=background, source=source, logo=logo).convert("RGB")
        except Exception as exc:
            stats["failed"] += 1
            print(f"  ! card {row['id']}: {exc}")
            continue
        stats["baked"] += 1
        if dry_run:
            continue
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=92, optimize=True)
        new_ref = store_bytes("cards", buf.getvalue(), "jpg")
        info = {"copy": legacy_copy(spec.to_dict()), "verification": None, "aspect": spec.aspect}
        try:
            with get_db_connection() as conn:
                conn.execute(
                    "UPDATE generated_cards SET studio_photo_url = ?, info_config = ?, poster_config = NULL WHERE id = ?",
                    (new_ref, json.dumps(info, ensure_ascii=False), row["id"]),
                )
                conn.commit()
        except Exception as exc:
            delete_photo(new_ref)
            stats["baked"] -= 1
            stats["failed"] += 1
            print(f"  ! card {row['id']}: {exc}")
            continue
        if row["studio_photo_url"]:
            to_delete.append(row["studio_photo_url"])  # the bare AI scene: the baked poster replaces it
    for ref in to_delete:  # only after every commit
        delete_photo(ref)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="only count what would be migrated")
    args = parser.parse_args()
    from dotenv import load_dotenv

    load_dotenv()  # before services.* are imported: OQILA_DB_PATH and OQILA_MEDIA_DIR may live in .env
    stats = migrate(dry_run=args.dry_run)
    prefix = "[dry run] would be" if args.dry_run else "done:"
    print(f"Posters {prefix} baked into pictures: {stats['baked']}, cleared (already AI pictures): {stats['cleared']}, "
          f"failed: {stats['failed']}")
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
