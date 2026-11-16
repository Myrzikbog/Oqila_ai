#!/usr/bin/env bash
# Backup of the database and the pictures. Run by cron every night (deploy.sh installs the job).
#
#   - the SQLite database through SQLite's online backup API (a consistent copy even while the app writes)
#   - media/ as a tar archive
#   - copies older than KEEP_DAYS (default 7) are deleted
#
# A backup on the same server does not survive the loss of the server: copy BACKUP_DIR elsewhere
# (README, "Резервные копии"). .session_secret and .uzum_key are NOT included on purpose: the key of the
# encrypted Uzum API keys must not sit next to the database it protects. Keep them (and .env) in your password manager.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
DB_PATH="${OQILA_DB_PATH:-$APP_DIR/oqila_ai.db}"
MEDIA_DIR="${OQILA_MEDIA_DIR:-$APP_DIR/media}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

if [ -f "$DB_PATH" ]; then
    # SQLite's online backup API: a consistent copy even while the app writes (python3 ships with the server image)
    python3 - "$DB_PATH" "$BACKUP_DIR/oqila_ai-$STAMP.db" <<'PY'
import sqlite3, sys
source = sqlite3.connect(sys.argv[1])
target = sqlite3.connect(sys.argv[2])
source.backup(target)
target.close()
source.close()
PY
    gzip -f "$BACKUP_DIR/oqila_ai-$STAMP.db"
fi
if [ -d "$MEDIA_DIR" ]; then
    tar -czf "$BACKUP_DIR/media-$STAMP.tar.gz" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"
fi

find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'oqila_ai-*.db.gz' -o -name 'media-*.tar.gz' \) -mtime "+$KEEP_DAYS" -delete
echo "backup $STAMP done: $(ls "$BACKUP_DIR" | wc -l) files in $BACKUP_DIR"
