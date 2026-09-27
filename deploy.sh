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
sudo apt-get install -y python3 python3-pip python3-venv git nginx curl ufw

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
    npm install
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

# 5. Setup systemd service for 24/7 background run
echo "⚙️ Step 4: Setting up systemd service..."
SERVICE_FILE="/etc/systemd/system/oqila-ai.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Oqila AI FastAPI Service
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable oqila-ai
sudo systemctl restart oqila-ai
echo "✅ oqila-ai systemd service enabled and started!"

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
