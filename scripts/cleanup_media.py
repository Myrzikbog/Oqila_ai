#!/usr/bin/env python3
"""
cleanup_media.py — housekeeping, run once a day by cron (deploy.sh installs the job).

1. Media files nobody refers to: pictures in media/ that no card, brand logo or Uzum record points to and that are
   older than 7 days (a file from the last 7 days may belong to a generation that is still being saved).
2. Old log rows: usage_logs older than 90 days, ai_calls older than 30 days, ai_reservations older than 7 days,
   handled Telegram update ids older than 7 days. (The AI quota windows are one day, so nothing in use is removed.)

Usage:  python scripts/cleanup_media.py [--dry-run] [--min-age-days 7] [--no-logs]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict, Set

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

LOG_RETENTION = (
    ("usage_logs", "created_at", 90),
    ("ai_calls", "created_at", 30),
    ("ai_reservations", "created_at", 7),
    ("telegram_updates", "created_at", 7),
)


def referenced_files() -> Set[str]:
    """Every "file:<subdir>/<name>" reference stored in the database, as a path relative to media/."""
    from services.database import get_db_connection

    refs: Set[str] = set()
    with get_db_connection() as conn:
        for table, column in (("generated_cards", "studio_photo_url"), ("generated_cards", "source_photo_url"), ("users", "brand_logo")):
            for row in conn.execute(f"SELECT {column} FROM {table} WHERE {column} LIKE 'file:%'"):
                refs.add(row[0][len("file:"):])
    return refs


def cleanup_media(min_age_days: int = 7, dry_run: bool = False) -> Dict[str, int]:
    from services.media_storage import media_dir

    root = media_dir()
    stats = {"scanned": 0, "orphans": 0, "bytes": 0, "kept_recent": 0}
    if not root.exists():
        return stats
    refs = referenced_files()
    cutoff = time.time() - min_age_days * 86400
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        stats["scanned"] += 1
        relative = path.relative_to(root).as_posix()
        if relative in refs:
            continue
        if path.stat().st_mtime > cutoff:
            stats["kept_recent"] += 1
            continue
        stats["orphans"] += 1
        stats["bytes"] += path.stat().st_size
        print(f"{'would delete' if dry_run else 'delete'}: {relative}")
        if not dry_run:
            path.unlink()
    return stats


def purge_logs(dry_run: bool = False) -> Dict[str, int]:
    from services.database import get_db_connection, init_db

    init_db()
    removed: Dict[str, int] = {}
    with get_db_connection() as conn:
        for table, column, days in LOG_RETENTION:
            where = f"{column} < datetime('now', '-{int(days)} days')"
            count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]
            removed[table] = count
            if count and not dry_run:
                conn.execute(f"DELETE FROM {table} WHERE {where}")
        conn.commit()
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="only list what would be removed")
    parser.add_argument("--min-age-days", type=int, default=7)
    parser.add_argument("--no-logs", action="store_true", help="do not purge old log rows")
    args = parser.parse_args()
    from dotenv import load_dotenv

    load_dotenv()  # OQILA_DB_PATH / OQILA_MEDIA_DIR may live in .env
    stats = cleanup_media(args.min_age_days, args.dry_run)
    verb = "would be" if args.dry_run else "were"
    print(f"media: {stats['scanned']} files checked, {stats['orphans']} orphans ({stats['bytes'] // 1024} KB) {verb} removed, "
          f"{stats['kept_recent']} recent unreferenced files kept")
    if not args.no_logs:
        removed = purge_logs(args.dry_run)
        print("log rows " + verb + " removed: " + ", ".join(f"{t}={n}" for t, n in removed.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
