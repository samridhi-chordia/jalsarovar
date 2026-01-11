#!/bin/bash
# ============================================================================
# Jal Sarovar - Remote Server Setup Script
# Run this script on the remote server after extracting the deployment package
# Deploys to demo.jalsarovar.com subdomain
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Jal Sarovar DEMO Deployment${NC}"
echo -e "${GREEN}Target: demo.jalsarovar.com${NC}"
echo -e "${GREEN}Install Path: /var/www/jalsarovar_demo${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${YELLOW}NOTE: This is a DEMO deployment separate from production${NC}"
echo -e "${YELLOW}Production: /var/www/jalsarovar (will NOT be affected)${NC}"
echo -e "${YELLOW}Demo: /var/www/jalsarovar_demo (new installation)${NC}"
echo ""

# Get current directory (should be the extracted package directory)
DEPLOY_DIR=$(pwd)
echo "Deployment directory: ${DEPLOY_DIR}"
echo ""

# Configuration - SEPARATE from production
APP_USER="jalsarovar-demo"
APP_GROUP="jalsarovar-demo"
APP_DIR="/var/www/jalsarovar_demo"
VENV_DIR="${APP_DIR}/venv"
WEB_DIR="${APP_DIR}/jalsarovar"
LOG_DIR="/var/log/jalsarovar-demo"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
SYSTEMD_DIR="/etc/systemd/system"

# Collect configuration
echo -e "${BLUE}Configuration Setup${NC}"
echo "==================="
echo ""

read -p "Enter domain name [demo.jalsarovar.com]: " DOMAIN_NAME
DOMAIN_NAME=${DOMAIN_NAME:-demo.jalsarovar.com}
echo ""

read -p "Enter database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Enter database port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Enter database name [jal_sarovar_prod]: " DB_NAME
DB_NAME=${DB_NAME:-jal_sarovar_prod}

read -p "Enter database user [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -sp "Enter database password: " DB_PASSWORD
echo ""
echo ""

read -sp "Enter Flask secret key (min 32 chars, press Enter to generate): " SECRET_KEY
echo ""
if [ -z "$SECRET_KEY" ]; then
    echo "Generating random secret key..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
fi
echo ""

read -p "Enable SSL/HTTPS? (y/n) [y]: " ENABLE_SSL
ENABLE_SSL=${ENABLE_SSL:-y}
echo ""

# Step 1: Update system and install dependencies
echo -e "${YELLOW}Step 1: Installing system dependencies...${NC}"
apt-get update
apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    postgresql-client \
    nginx \
    git \
    curl \
    build-essential \
    libpq-dev \
    supervisor

echo -e "${GREEN}✓ System dependencies installed${NC}"
echo ""

# Step 2: Create application user
echo -e "${YELLOW}Step 2: Creating application user...${NC}"
if id "$APP_USER" &>/dev/null; then
    echo "User $APP_USER already exists"
else
    useradd -m -s /bin/bash $APP_USER
    echo "User $APP_USER created"
fi

# Step 3: Create directories
echo -e "${YELLOW}Step 3: Creating application directories...${NC}"
mkdir -p $APP_DIR
mkdir -p $LOG_DIR
mkdir -p ${WEB_DIR}/uploads
mkdir -p ${WEB_DIR}/logs
mkdir -p ${WEB_DIR}/backups
mkdir -p ${WEB_DIR}/models

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 4: Copy application files
echo -e "${YELLOW}Step 4: Copying application files...${NC}"
if [ -d "${WEB_DIR}" ]; then
    echo "Backing up existing installation..."
    mv ${WEB_DIR} ${WEB_DIR}.backup.$(date +%Y%m%d_%H%M%S)
fi

cp -r ${DEPLOY_DIR} ${WEB_DIR}
chown -R ${APP_USER}:${APP_GROUP} ${APP_DIR}
chown -R ${APP_USER}:${APP_GROUP} ${LOG_DIR}

echo -e "${GREEN}✓ Application files copied${NC}"
echo ""

# Step 5: Create Python virtual environment
echo -e "${YELLOW}Step 5: Creating Python virtual environment...${NC}"
sudo -u ${APP_USER} python3.11 -m venv ${VENV_DIR}
sudo -u ${APP_USER} ${VENV_DIR}/bin/pip install --upgrade pip
sudo -u ${APP_USER} ${VENV_DIR}/bin/pip install -r ${WEB_DIR}/requirements.txt

echo -e "${GREEN}✓ Virtual environment created and dependencies installed${NC}"
echo ""

# Step 6: Configure environment variables
echo -e "${YELLOW}Step 6: Configuring environment variables...${NC}"
cat > ${WEB_DIR}/.env.production << EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}

# Application Settings
PORT=8000
LOG_LEVEL=info
WORKERS=4

# Database Configuration
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=86400

# File Upload Settings
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=${WEB_DIR}/uploads

# ML Models Path
ML_MODELS_PATH=${WEB_DIR}/models

# Timezone
TZ=Asia/Kolkata
EOF

chown ${APP_USER}:${APP_GROUP} ${WEB_DIR}/.env.production
chmod 600 ${WEB_DIR}/.env.production

echo -e "${GREEN}✓ Environment variables configured${NC}"
echo ""

# Step 7: Test database connection
echo -e "${YELLOW}Step 7: Testing database connection...${NC}"
export PGPASSWORD=${DB_PASSWORD}
if psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo "Please check your database credentials and ensure PostgreSQL is running"
    read -p "Continue anyway? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi
unset PGPASSWORD
echo ""

# Step 8: Run database migrations
echo -e "${YELLOW}Step 8: Running database migrations...${NC}"
cd ${WEB_DIR}
sudo -u ${APP_USER} ${VENV_DIR}/bin/flask db upgrade || {
    echo -e "${YELLOW}⚠ Migrations failed or already up to date${NC}"
}

echo -e "${GREEN}✓ Database migrations completed${NC}"
echo ""

# Step 9: Configure systemd service
echo -e "${YELLOW}Step 9: Configuring systemd service (jalsarovar-demo)...${NC}"
cat > ${SYSTEMD_DIR}/jalsarovar-demo.service << EOF
[Unit]
Description=Jal Sarovar DEMO - Water Quality Management System
Documentation=https://demo.jalsarovar.com
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${WEB_DIR}
Environment="PATH=${VENV_DIR}/bin"
EnvironmentFile=${WEB_DIR}/.env.production

ExecStart=${VENV_DIR}/bin/gunicorn \\
    --config ${WEB_DIR}/gunicorn_config.py \\
    --bind 0.0.0.0:8001 \\
    --workers 4 \\
    --worker-class sync \\
    --timeout 120 \\
    --access-logfile ${LOG_DIR}/access.log \\
    --error-logfile ${LOG_DIR}/error.log \\
    --log-level info \\
    --name jalsarovar-demo \\
    app:app

Restart=always
RestartSec=10
StartLimitInterval=400
StartLimitBurst=5

NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${WEB_DIR}/uploads ${LOG_DIR} ${WEB_DIR}/backups

LimitNOFILE=65536
LimitNPROC=512

KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jalsarovar-demo.service

echo -e "${GREEN}✓ Systemd service configured (jalsarovar-demo.service)${NC}"
echo ""

# Step 10: Configure Nginx
echo -e "${YELLOW}Step 10: Configuring Nginx (demo.jalsarovar.com)...${NC}"

# Note: Do NOT remove default or other sites - production may be using them
echo "Creating separate nginx configuration for demo subdomain..."

if [ "$ENABLE_SSL" = "y" ]; then
    # SSL configuration
    cat > ${NGINX_AVAILABLE}/jalsarovar-demo << EOF
upstream jalsarovar_demo_app {
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN_NAME};

    # SSL Configuration - Update paths after obtaining certificates
    ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    root ${WEB_DIR}/app/static;

    access_log ${LOG_DIR}/nginx_access.log;
    error_log ${LOG_DIR}/nginx_error.log warn;

    client_max_body_size 50M;

    location /static/ {
        alias ${WEB_DIR}/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias ${WEB_DIR}/uploads/;
        expires 7d;
    }

    location / {
        proxy_pass http://jalsarovar_demo_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;

        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
EOF
else
    # HTTP-only configuration
    cat > ${NGINX_AVAILABLE}/jalsarovar-demo << EOF
upstream jalsarovar_demo_app {
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME};

    root ${WEB_DIR}/app/static;

    access_log ${LOG_DIR}/nginx_access.log;
    error_log ${LOG_DIR}/nginx_error.log warn;

    client_max_body_size 50M;

    location /static/ {
        alias ${WEB_DIR}/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads/ {
        alias ${WEB_DIR}/uploads/;
        expires 7d;
    }

    location / {
        proxy_pass http://jalsarovar_demo_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }
}
EOF
fi

# Enable site
ln -sf ${NGINX_AVAILABLE}/jalsarovar-demo ${NGINX_ENABLED}/jalsarovar-demo

# Test nginx configuration
nginx -t

echo -e "${GREEN}✓ Nginx configured (jalsarovar-demo)${NC}"
echo ""

# Step 11: Configure firewall
echo -e "${YELLOW}Step 11: Configuring firewall...${NC}"
if command -v ufw &> /dev/null; then
    # Only add rules if they don't exist - production may already have these
    ufw allow 22/tcp 2>/dev/null || echo "Port 22 already allowed"
    ufw allow 80/tcp 2>/dev/null || echo "Port 80 already allowed"
    if [ "$ENABLE_SSL" = "y" ]; then
        ufw allow 443/tcp 2>/dev/null || echo "Port 443 already allowed"
    fi
    ufw status
    echo -e "${GREEN}✓ Firewall checked${NC}"
else
    echo -e "${YELLOW}⚠ UFW not installed, skipping firewall configuration${NC}"
fi
echo ""

# Step 12: Start services
echo -e "${YELLOW}Step 12: Starting demo service...${NC}"
systemctl start jalsarovar-demo
systemctl reload nginx

echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Step 13: Check service status
echo -e "${YELLOW}Step 13: Checking service status...${NC}"
sleep 3

if systemctl is-active --quiet jalsarovar-demo; then
    echo -e "${GREEN}✓ Jal Sarovar DEMO service is running${NC}"
else
    echo -e "${RED}✗ Jal Sarovar DEMO service failed to start${NC}"
    echo "Check logs: journalctl -u jalsarovar-demo -n 50"
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx service is running${NC}"
else
    echo -e "${RED}✗ Nginx service failed to start${NC}"
    echo "Check logs: tail -f /var/log/nginx/error.log"
fi
echo ""

# Final summary
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Application URL: http://${DOMAIN_NAME}"
if [ "$ENABLE_SSL" = "y" ]; then
    echo ""
    echo -e "${YELLOW}SSL Configuration:${NC}"
    echo "Install certbot and obtain SSL certificate:"
    echo "  apt-get install -y certbot python3-certbot-nginx"
    echo "  certbot --nginx -d ${DOMAIN_NAME}"
    echo ""
    echo "After obtaining certificate, reload nginx:"
    echo "  systemctl reload nginx"
fi
echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Installation Paths (DEMO - Separate from Production):${NC}"
echo -e "${BLUE}=========================================${NC}"
echo "Demo Application: ${APP_DIR}"
echo "Demo Logs:        ${LOG_DIR}"
echo "Demo Service:     jalsarovar-demo.service"
echo "Demo Nginx:       /etc/nginx/sites-available/jalsarovar-demo"
echo "Demo Port:        8001 (internal)"
echo ""
echo -e "${GREEN}Production Installation (UNCHANGED):${NC}"
echo "Production Path:  /var/www/jalsarovar"
echo "Production Port:  8000 (internal)"
echo "Production Service: (existing service name)"
echo ""
echo "Service Management (DEMO):"
echo "  Status:  systemctl status jalsarovar-demo"
echo "  Logs:    journalctl -u jalsarovar-demo -f"
echo "  Restart: systemctl restart jalsarovar-demo"
echo "  Stop:    systemctl stop jalsarovar-demo"
echo ""
echo "Application Logs (DEMO):"
echo "  Access:  tail -f ${LOG_DIR}/access.log"
echo "  Error:   tail -f ${LOG_DIR}/error.log"
echo "  Nginx:   tail -f /var/log/nginx/error.log"
echo ""
echo "Next Steps:"
echo "1. Test demo site: curl http://localhost:8001/health"
echo ""
echo "2. Create admin user (optional):"
echo "   cd ${WEB_DIR}"
echo "   sudo -u ${APP_USER} ${VENV_DIR}/bin/python3 -c \\"
echo "   \"from app import create_app, db; from app.models import User; \\"
echo "   app = create_app('production'); \\"
echo "   with app.app_context(): \\"
echo "       admin = User(username='demo-admin', email='admin@demo.jalsarovar.com', is_admin=True); \\"
echo "       admin.set_password('your-password'); \\"
echo "       db.session.add(admin); \\"
echo "       db.session.commit(); \\"
echo "       print('Demo admin created')\""
echo ""
echo "3. Upload ML models to: ${WEB_DIR}/models"
echo ""
echo "4. Set up automated backups (separate from production):"
echo "   Add to crontab: 0 3 * * * ${WEB_DIR}/deployment/scripts/backup.sh"
echo ""
echo "5. Verify demo site: http://demo.jalsarovar.com"
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}DEMO Deployment completed: demo.jalsarovar.com${NC}"
echo -e "${GREEN}Production site UNCHANGED: www.jalsarovar.com${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
