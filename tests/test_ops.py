"""Phase 5: media cleanup, log purge, backup script, deployment files."""
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from conftest import login

ROOT = Path(__file__).resolve().parent.parent


def _run(*args, **kw):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "cleanup_media.py"), *args], capture_output=True, text=True, cwd=str(ROOT), env={**os.environ}, **kw)


def _age(path: Path, days: int) -> None:
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def test_cleanup_removes_only_old_unreferenced_files(client):
    from services.database import DB_PATH, save_generated_card, set_brand_logo
    from services.media_storage import media_dir, resolve_photo, store_bytes

    who = login(client, tg_id=850001)
    used_photo, used_source, used_logo = (store_bytes("cards", b"a", "jpg"), store_bytes("source", b"b", "jpg"), store_bytes("brand", b"c", "png"))
    save_generated_card(title="t", description="", price_tag="", hashtags=[], marketing_tip="", user_id=who["user_id"],
                        source_photo_url=used_source)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE generated_cards SET studio_photo_url = ? WHERE user_id = ?", (used_photo, who["user_id"]))
    set_brand_logo(who["user_id"], used_logo)
    orphan_old, orphan_recent = store_bytes("cards", b"old", "jpg"), store_bytes("cards", b"new", "jpg")
    for ref in (used_photo, used_source, used_logo, orphan_old):
        _age(resolve_photo(ref), 30)

    dry = _run("--dry-run", "--no-logs")
    assert dry.returncode == 0 and "would delete" in dry.stdout and orphan_old[len("file:"):] in dry.stdout and "1 orphans" in dry.stdout, dry.stdout + dry.stderr
    assert resolve_photo(orphan_old), "a dry run deletes nothing"
    real = _run("--no-logs")
    assert real.returncode == 0 and "1 orphans" in real.stdout, real.stdout + real.stderr
    assert resolve_photo(orphan_old) is None
    assert all(resolve_photo(r) for r in (used_photo, used_source, used_logo, orphan_recent)), "referenced and recent files stay"
    assert media_dir().exists()
    assert "0 orphans" in _run("--no-logs").stdout


def test_old_log_rows_are_purged_and_fresh_ones_stay(client):
    from services.database import DB_PATH

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO usage_logs (event_type, created_at) VALUES ('old_event', datetime('now', '-120 days'))")
        conn.execute("INSERT INTO usage_logs (event_type, created_at) VALUES ('new_event', datetime('now', '-10 days'))")
        conn.execute("INSERT INTO ai_calls (kind, created_at) VALUES ('text', datetime('now', '-45 days'))")
        conn.execute("INSERT INTO ai_reservations (user_id, event_type, status, created_at) VALUES (1, 'generate_card', 'ok', datetime('now', '-2 hours'))")
        conn.execute("INSERT INTO ai_reservations (user_id, event_type, status, created_at) VALUES (1, 'generate_card', 'ok', datetime('now', '-9 days'))")
    dry = _run("--dry-run")
    assert "usage_logs=1" in dry.stdout and "ai_reservations=1" in dry.stdout
    with sqlite3.connect(DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM usage_logs WHERE event_type = 'old_event'").fetchone()[0] == 1
    assert _run().returncode == 0
    with sqlite3.connect(DB_PATH) as conn:
        assert conn.execute("SELECT COUNT(*) FROM usage_logs WHERE event_type = 'old_event'").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM usage_logs WHERE event_type = 'new_event'").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM ai_calls WHERE created_at < datetime('now', '-30 days')").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM ai_reservations WHERE created_at > datetime('now', '-1 day')").fetchone()[0] >= 1, "the quota window is untouched"


def test_backup_script_makes_a_consistent_copy_and_rotates(tmp_path):
    db, media, backups = tmp_path / "app.db", tmp_path / "media", tmp_path / "backups"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()
    conn.close()
    (media / "cards").mkdir(parents=True)
    (media / "cards" / "a.jpg").write_bytes(b"jpg")
    backups.mkdir()
    stale = backups / "oqila_ai-20200101-000000.db.gz"
    stale.write_bytes(b"old")
    _age(stale, 30)
    env = {**os.environ, "OQILA_DB_PATH": str(db), "OQILA_MEDIA_DIR": str(media), "BACKUP_DIR": str(backups), "KEEP_DAYS": "7"}
    res = subprocess.run(["bash", str(ROOT / "scripts" / "backup.sh")], capture_output=True, text=True, env=env)
    assert res.returncode == 0, res.stderr
    names = sorted(p.name for p in backups.iterdir())
    assert any(n.startswith("oqila_ai-") and n.endswith(".db.gz") for n in names) and any(n.startswith("media-") for n in names)
    assert stale.name not in names, "copies older than KEEP_DAYS are deleted"
    import gzip

    restored = tmp_path / "restored.db"
    restored.write_bytes(gzip.decompress(next(p for p in backups.iterdir() if p.name.endswith(".db.gz") and "2020" not in p.name).read_bytes()))
    assert sqlite3.connect(restored).execute("SELECT x FROM t").fetchone()[0] == 42


def test_deployment_files():
    service = (ROOT / "oqila-ai.service").read_text(encoding="utf-8")
    assert "User=oqila" in service and "User=root" not in service and "NoNewPrivileges=true" in service
    nginx = (ROOT / "nginx.conf").read_text(encoding="utf-8")
    for needle in ("Strict-Transport-Security", "Content-Security-Policy", "Referrer-Policy", "limit_req ", "proxy_read_timeout 180s", "frame-ancestors"):
        assert needle in nginx, needle
    assert 'Connection "upgrade"' not in nginx and "Upgrade $http_upgrade" not in nginx, "no WebSocket headers: they disable keep-alive"
    assert "script-src 'self' https://telegram.org" in nginx and "unsafe-eval" not in nginx
    deploy = (ROOT / "deploy.sh").read_text(encoding="utf-8")
    for needle in ("useradd", "ufw allow", "migrate_posters.py", "backup.sh", "cleanup_media.py", "journald"):
        assert needle in deploy, needle
    assert not re.search(r"User=\$\(whoami\)", deploy), "the service must not run as the person who deploys"


def test_dependencies_are_pinned():
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            assert "==" in line and ">=" not in line, f"unpinned: {line}"
    package = (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    assert '"engines"' in package and '"lucide-react"' in package.split('"devDependencies"')[0], "lucide-react is a runtime dependency"
    assert '"ignorePatterns"' in (ROOT / "frontend" / ".oxlintrc.json").read_text(encoding="utf-8")
