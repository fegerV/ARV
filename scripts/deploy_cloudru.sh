#!/usr/bin/env bash
# ============================================================================
# Vertex AR — Deployment Script for Cloud.ru (Ubuntu 24.04)
# ============================================================================
# Usage:
#   1. SSH into the server:  ssh aruser@192.144.12.68
#   2. Run as root:          sudo bash deploy_cloudru.sh
#
# This script:
#   - Installs system packages (Python 3.11, PostgreSQL 16, Nginx, Certbot, etc.)
#   - Creates a dedicated 'arv' system user
#   - Sets up PostgreSQL database
#   - Clones the repo & installs Python dependencies
#   - Creates persistent storage directories
#   - Configures Nginx with HTTPS (Let's Encrypt)
#   - Registers a systemd service for auto-restart
#   - Runs Alembic migrations
#   - Starts the application
# ============================================================================

set -euo pipefail

# ========================= CONFIGURATION ====================================
DOMAIN="ar.neuroimagen.ru"
APP_DIR="/opt/arv/app"
VENV_DIR="/opt/arv/venv"
STORAGE_DIR="/opt/arv/storage"
ARV_USER="arv"
GIT_REPO="https://github.com/nicktretyakov/ARV.git"
GIT_BRANCH="main"

DB_NAME="vertex_ar"
DB_USER="vertex_ar"
# Generate random password if not supplied
DB_PASS="${DB_PASS:-$(openssl rand -hex 16)}"

ADMIN_PASS="${ADMIN_PASS:-$(openssl rand -hex 8)}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@neuroimagen.ru}"
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[ARV]${NC} $*"; }
warn() { echo -e "${YELLOW}[ARV WARN]${NC} $*"; }
err()  { echo -e "${RED}[ARV ERROR]${NC} $*" >&2; }

# Check root
if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root. Use: sudo bash $0"
    exit 1
fi

# ========================= 1. SYSTEM PACKAGES ===============================
log "Step 1/10: Installing system packages..."

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

apt-get install -y -qq \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx certbot python3-certbot-nginx \
    redis-server \
    ffmpeg \
    git curl wget htop ufw \
    gcc g++ build-essential libffi-dev libssl-dev

log "System packages installed."

# ========================= 2. FIREWALL ======================================
log "Step 2/10: Configuring firewall (UFW)..."

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

log "Firewall configured (SSH, HTTP, HTTPS)."

# ========================= 3. CREATE APP USER ================================
log "Step 3/10: Creating application user '${ARV_USER}'..."

if ! id "$ARV_USER" &>/dev/null; then
    useradd --system --create-home --home-dir /opt/arv --shell /bin/bash "$ARV_USER"
    log "User '${ARV_USER}' created."
else
    log "User '${ARV_USER}' already exists."
fi

# ========================= 4. POSTGRESQL =====================================
log "Step 4/10: Configuring PostgreSQL..."

systemctl enable postgresql
systemctl start postgresql

# Create user and database if they don't exist
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';"

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

log "PostgreSQL configured: db=${DB_NAME}, user=${DB_USER}"

# ========================= 5. CLONE / UPDATE REPO ============================
log "Step 5/10: Setting up application code..."

mkdir -p /opt/arv
chown "$ARV_USER":"$ARV_USER" /opt/arv

if [[ -d "$APP_DIR/.git" ]]; then
    log "Repository exists, pulling latest changes..."
    sudo -u "$ARV_USER" git -C "$APP_DIR" fetch origin
    sudo -u "$ARV_USER" git -C "$APP_DIR" reset --hard "origin/${GIT_BRANCH}"
else
    log "Cloning repository..."
    sudo -u "$ARV_USER" git clone -b "$GIT_BRANCH" "$GIT_REPO" "$APP_DIR"
fi

log "Application code ready at ${APP_DIR}"

# ========================= 6. PYTHON VENV & DEPENDENCIES ====================
log "Step 6/10: Setting up Python virtual environment..."

if [[ ! -d "$VENV_DIR" ]]; then
    sudo -u "$ARV_USER" python3 -m venv "$VENV_DIR"
fi

sudo -u "$ARV_USER" "$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools -q
sudo -u "$ARV_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q

log "Python dependencies installed."

# ========================= 7. STORAGE & .ENV =================================
log "Step 7/10: Configuring storage and environment..."

# Create storage directories
mkdir -p "${STORAGE_DIR}"/{content,thumbnails,markers,videos,temp}
chown -R "$ARV_USER":"$ARV_USER" "$STORAGE_DIR"

# Create /tmp/prometheus_multiproc for metrics
mkdir -p /tmp/prometheus_multiproc
chown "$ARV_USER":"$ARV_USER" /tmp/prometheus_multiproc

# Generate .env from template
cat > "$APP_DIR/.env" <<ENVEOF
# ===== Vertex AR — Production Environment =====
# Auto-generated by deploy_cloudru.sh at $(date -Iseconds)

ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

SECRET_KEY=${SECRET_KEY}
ADMIN_DEFAULT_PASSWORD=${ADMIN_PASS}
ADMIN_EMAIL=admin@vertexar.com

PUBLIC_URL=https://${DOMAIN}

SSL_KEYFILE=
SSL_CERTFILE=

CORS_ORIGINS=https://${DOMAIN}

STORAGE_BASE_PATH=${STORAGE_DIR}
LOCAL_STORAGE_PATH=${STORAGE_DIR}
LOCAL_STORAGE_PUBLIC_URL=https://${DOMAIN}/storage

REDIS_URL=redis://localhost:6379/0

ANDROID_APP_PACKAGE=ru.neuroimagen.arviewer
ANDROID_APP_SHA256_FINGERPRINTS=

SENTRY_DSN=
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
ENVEOF

chown "$ARV_USER":"$ARV_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

log "Storage and .env configured."

# ========================= 8. DATABASE MIGRATIONS ============================
log "Step 8/10: Running database migrations..."

cd "$APP_DIR"
sudo -u "$ARV_USER" PYTHONPATH="$APP_DIR" "$VENV_DIR/bin/alembic" upgrade head || {
    warn "Alembic migration failed. Trying to create tables directly..."
    sudo -u "$ARV_USER" PYTHONPATH="$APP_DIR" "$VENV_DIR/bin/python" -c "
import asyncio
from app.core.database import engine, Base
from app.models import *
async def create_all():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(create_all())
print('Tables created successfully.')
"
}

log "Database ready."

# ========================= 9. NGINX + SSL ====================================
log "Step 9/10: Configuring Nginx and SSL..."

# Copy Nginx config
cp "$APP_DIR/deploy/nginx/arv.conf" /etc/nginx/sites-available/arv.conf

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/arv.conf /etc/nginx/sites-enabled/arv.conf

# Create certbot webroot
mkdir -p /var/www/certbot

# Test Nginx config WITHOUT ssl first (cert might not exist yet)
# Temporarily create a simple HTTP-only config for certificate issuance
cat > /etc/nginx/sites-available/arv-temp-http.conf <<TMPNGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
TMPNGINX

# If cert doesn't exist yet, start with HTTP-only for certbot
if [[ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
    ln -sf /etc/nginx/sites-available/arv-temp-http.conf /etc/nginx/sites-enabled/arv.conf
    nginx -t && systemctl restart nginx

    log "Obtaining SSL certificate via Certbot..."
    certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        -d "$DOMAIN" \
        --email "$CERTBOT_EMAIL" \
        --agree-tos \
        --non-interactive || {
        warn "Certbot failed. Make sure DNS A-record for ${DOMAIN} points to this server's IP."
        warn "You can run certbot manually later: certbot certonly --nginx -d ${DOMAIN}"
    }

    # Now switch to full HTTPS config
    ln -sf /etc/nginx/sites-available/arv.conf /etc/nginx/sites-enabled/arv.conf
fi

nginx -t && systemctl restart nginx
systemctl enable nginx

# Set up auto-renewal
systemctl enable certbot.timer 2>/dev/null || true

log "Nginx configured."

# ========================= 10. SYSTEMD SERVICE ==============================
log "Step 10/10: Setting up systemd service..."

cp "$APP_DIR/deploy/systemd/arv.service" /etc/systemd/system/arv.service

systemctl daemon-reload
systemctl enable arv.service
systemctl restart arv.service

# Wait for service to start
sleep 3

if systemctl is-active --quiet arv.service; then
    log "Service started successfully!"
else
    warn "Service may not have started. Check logs: journalctl -u arv -f"
fi

# ========================= SUMMARY ==========================================
echo ""
echo "============================================================"
echo -e "${GREEN}  Vertex AR — Deployment Complete!${NC}"
echo "============================================================"
echo ""
echo "  Domain:    https://${DOMAIN}"
echo "  App dir:   ${APP_DIR}"
echo "  Storage:   ${STORAGE_DIR}"
echo "  Venv:      ${VENV_DIR}"
echo ""
echo "  Database:  ${DB_NAME} (PostgreSQL)"
echo "  DB User:   ${DB_USER}"
echo "  DB Pass:   ${DB_PASS}"
echo ""
echo "  Admin:     admin@vertexar.com"
echo "  Admin pw:  ${ADMIN_PASS}"
echo "  Secret:    ${SECRET_KEY:0:16}..."
echo ""
echo "  Useful commands:"
echo "    journalctl -u arv -f          # View app logs"
echo "    systemctl restart arv         # Restart app"
echo "    systemctl status arv          # Check status"
echo "    sudo -u arv ${VENV_DIR}/bin/alembic upgrade head  # Run migrations"
echo ""
echo "  IMPORTANT: Save the credentials above!"
echo "============================================================"
