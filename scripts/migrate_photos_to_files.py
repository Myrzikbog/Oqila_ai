"""Move card photos stored inline as base64 data: URLs out of SQLite into media/ files.

Safe to run repeatedly: only rows that still hold a data: URL are touched.
Usage: python scripts/migrate_photos_to_files.py [--vacuum]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from services.database import DB_PATH, get_db_connection, init_db  # noqa: E402
from services.media_storage import store_photo  # noqa: E402


def migrate(vacuum: bool = False) -> int:
    init_db()
    moved = 0
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, studio_photo_url FROM generated_cards WHERE studio_photo_url LIKE 'data:%'"
        ).fetchall()
        for row in rows:
            ref = store_photo(row["studio_photo_url"])
            if ref and ref.startswith("file:"):
                conn.execute("UPDATE generated_cards SET studio_photo_url = ? WHERE id = ?", (ref, row["id"]))
                moved += 1
        conn.commit()
        if vacuum and moved:
            conn.execute("VACUUM")
    print(f"Moved {moved} photo(s) from {DB_PATH} to files.")
    return moved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vacuum", action="store_true", help="shrink the database file afterwards")
    migrate(vacuum=parser.parse_args().vacuum)
