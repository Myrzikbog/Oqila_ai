#!/usr/bin/env bash
# ==============================================================================
# deploy.sh — Oqila AI Deployment Script for Ubuntu / Debian VDS
# Oqila AI Platform
# ==============================================================================
set -e

echo "🌿 ============================================"
echo "   Deploying Oqila AI (Tadbirkor Qizlar) on VDS"
echo "================================================"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "📂 Project directory: $PROJECT_DIR"

# 1. Update OS packages & install runtime dependencies
echo "📦 Step 1: Checking system packages..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git nginx curl ufw cron

# 2. Setup Python Virtual Environment
echo "🐍 Step 2: Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Created venv"
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Build React Frontend
if [ -d "frontend" ]; then
    echo "⚛️ Step 2.5: Building React + Vite Frontend..."
    if ! command -v npm &> /dev/null; then
        echo "Installing Node.js & npm..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    cd frontend
    npm ci
    npm run build
    cd ..
    echo "✅ React Frontend built successfully!"
fi

# 4. Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying .env.example..."
    cp .env.example .env
    echo "❗ Please edit .env with your GEMINI_API_KEY and TELEGRAM_BOT_TOKEN"
fi
chmod 600 .env

# Generate strong secrets once if they are missing or empty (never overwrite existing values)
ensure_secret() {
    local name="$1"
    if ! grep -qE "^${name}=.{16,}" .env; then
        local value
        value="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
        sed -i "/^${name}=/d" .env
        echo "${name}=${value}" >> .env
        echo "🔐 Generated ${name} in .env"
    fi
}
ensure_secret ADMIN_SECRET_KEY
ensure_secret SESSION_SECRET
ensure_secret TELEGRAM_WEBHOOK_SECRET

# Move card photos stored inline in SQLite (older versions) into media/ files
python scripts/migrate_photos_to_files.py
# Old server-drawn posters become ordinary pictures (idempotent: a second run finds nothing to do)
python scripts/migrate_posters.py

# 5. A dedicated system user, the systemd service, backups, housekeeping, journald limits
echo "⚙️ Step 4: Setting up the service..."
APP_USER="oqila"
if ! id "$APP_USER" &>/dev/null; then
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
    echo "✅ Created system user $APP_USER"
fi
# The service writes only to the database, media/, the generated secret files and the poller lock
mkdir -p media backups
sudo chown -R "$APP_USER":"$APP_USER" media backups
for f in oqila_ai.db oqila_ai.db-wal oqila_ai.db-shm .session_secret .uzum_key .uzum_poller.lock; do
    if [ -e "$f" ]; then sudo chown "$APP_USER":"$APP_USER" "$f"; fi
done
sudo chown root:"$APP_USER" .env
sudo chmod 640 .env
# The directory itself must be writable for the database's journal files and the lock file
sudo chown "$APP_USER":"$APP_USER" "$PROJECT_DIR"
SERVICE_FILE="/etc/systemd/system/oqila-ai.service"

sudo bash -c "cat > $SERVICE_FILE" <<UNIT
[Unit]
Description=Oqila AI FastAPI Service
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
UNIT

# Nightly backup (03:15) and housekeeping (03:40): old log rows and pictures no card refers to
sudo bash -c "cat > /etc/cron.d/oqila-ai" <<CRON
15 3 * * * $APP_USER $PROJECT_DIR/scripts/backup.sh >> $PROJECT_DIR/backups/backup.log 2>&1
40 3 * * * $APP_USER cd $PROJECT_DIR && $PROJECT_DIR/venv/bin/python scripts/cleanup_media.py >> $PROJECT_DIR/backups/cleanup.log 2>&1
CRON
sudo chmod 644 /etc/cron.d/oqila-ai

# The journal must not fill the disk
sudo mkdir -p /etc/systemd/journald.conf.d
sudo bash -c "cat > /etc/systemd/journald.conf.d/oqila.conf" <<JOURNAL
[Journal]
SystemMaxUse=500M
MaxRetentionSec=1month
JOURNAL
sudo systemctl restart systemd-journald

sudo systemctl daemon-reload
sudo systemctl enable oqila-ai
sudo systemctl restart oqila-ai
echo "✅ oqila-ai systemd service enabled and started!"

# 5b. Firewall: only SSH, HTTP and HTTPS are reachable from outside (uvicorn listens on 127.0.0.1 only)
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 5c. Nginx: installed when WEBAPP_URL in .env names the domain (the config template has a placeholder)
DOMAIN="$(grep -E '^WEBAPP_URL=' .env | head -1 | sed -E 's#^WEBAPP_URL=(https?://)?([^/:[:space:]]+).*#\2#' || true)"
if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "your-domain.com" ] && [[ "$DOMAIN" != WEBAPP_URL* ]]; then
    sed "s/your-domain.com/$DOMAIN/g" nginx.conf | sudo tee /etc/nginx/sites-available/oqila-ai > /dev/null
    sudo ln -sf /etc/nginx/sites-available/oqila-ai /etc/nginx/sites-enabled/oqila-ai
    if sudo nginx -t; then
        sudo systemctl reload nginx
        echo "✅ Nginx configured for $DOMAIN (run certbot for HTTPS, see nginx.conf)"
    else
        echo "⚠️  nginx -t failed: fix /etc/nginx/sites-available/oqila-ai"
    fi
else
    echo "ℹ️  Set WEBAPP_URL=https://your-domain in .env and run deploy.sh again to install the Nginx config."
fi

# 5. Check local service status
sleep 2
if curl -s http://127.0.0.1:8000/health | grep -q "healthy"; then
    echo "✅ FastAPI is healthy on http://127.0.0.1:8000"
else
    echo "⚠️  Warning: FastAPI health check did not respond immediately. Check: sudo journalctl -u oqila-ai -f"
fi

echo ""
echo "🎉 Deployment complete!"
echo "👉 To configure Nginx and SSL (Let's Encrypt), see instructions in nginx.conf"
echo "👉 View service logs: sudo journalctl -u oqila-ai -f"
echo "👉 Restart service:   sudo systemctl restart oqila-ai"
