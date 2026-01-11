# Adapt Deployment to Use /var/www/jalsarovar_demo/ (Flat Structure)

## Current Situation

Files are located at:
```
/var/www/jalsarovar_demo/
├── app/
│   ├── models/
│   └── ...
├── config.py
├── app.py
├── requirements.txt
└── ...
```

Instead of the expected:
```
/var/www/jalsarovar_demo/
└── jalsarovar/
    ├── app/
    ├── config.py
    └── ...
```

---

## Required Changes

### 1. Update Systemd Service File

**File**: `/etc/systemd/system/jalsarovar-demo.service`

```bash
sudo nano /etc/systemd/system/jalsarovar-demo.service
```

**Change these lines:**

```ini
[Service]
Type=notify
User=jalsarovar-demo
Group=jalsarovar-demo

# OLD:
WorkingDirectory=/var/www/jalsarovar_demo/jalsarovar

# NEW:
WorkingDirectory=/var/www/jalsarovar_demo

Environment="PATH=/var/www/jalsarovar_demo/venv/bin"

# OLD:
EnvironmentFile=/var/www/jalsarovar_demo/jalsarovar/.env.production

# NEW:
EnvironmentFile=/var/www/jalsarovar_demo/.env.production

# OLD:
ExecStart=/var/www/jalsarovar_demo/venv/bin/gunicorn \
    --config /var/www/jalsarovar_demo/jalsarovar/gunicorn_config.py \
    --bind 0.0.0.0:8001 \
    --workers 4 \
    --name jalsarovar-demo \
    app:app

# NEW:
ExecStart=/var/www/jalsarovar_demo/venv/bin/gunicorn \
    --config /var/www/jalsarovar_demo/gunicorn_config.py \
    --bind 0.0.0.0:8001 \
    --workers 4 \
    --name jalsarovar-demo \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Complete working service file:**

```ini
[Unit]
Description=Jal Sarovar DEMO - Water Quality Management System
Documentation=https://demo.jalsarovar.com
After=network.target postgresql.service

[Service]
Type=notify
User=jalsarovar-demo
Group=jalsarovar-demo
WorkingDirectory=/var/www/jalsarovar_demo
Environment="PATH=/var/www/jalsarovar_demo/venv/bin"
EnvironmentFile=/var/www/jalsarovar_demo/.env.production

ExecStart=/var/www/jalsarovar_demo/venv/bin/gunicorn \
    --config /var/www/jalsarovar_demo/gunicorn_config.py \
    --bind 0.0.0.0:8001 \
    --workers 4 \
    --name jalsarovar-demo \
    app:app

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=jalsarovar-demo

[Install]
WantedBy=multi-user.target
```

**Save and reload:**
```bash
sudo systemctl daemon-reload
```

---

### 2. Create/Update Environment File

**File**: `/var/www/jalsarovar_demo/.env.production`

Create the environment file at the root level:

```bash
sudo nano /var/www/jalsarovar_demo/.env.production
```

**Add these contents:**

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=your-strong-secret-key-here

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jal_sarovar_demo
DB_USER=postgres
DB_PASSWORD=your-database-password

# Application Settings
PORT=8001
LOG_LEVEL=info
WORKERS=4

# Security Settings
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Paths (updated for flat structure)
UPLOAD_FOLDER=/var/www/jalsarovar_demo/uploads
ML_MODELS_PATH=/var/www/jalsarovar_demo/app/ml/models

# Timezone
TZ=Asia/Kolkata
```

**Set correct permissions:**
```bash
sudo chown jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo/.env.production
sudo chmod 600 /var/www/jalsarovar_demo/.env.production
```

---

### 3. Update Gunicorn Config (If Needed)

**File**: `/var/www/jalsarovar_demo/gunicorn_config.py`

Check if paths are correct:

```bash
cat /var/www/jalsarovar_demo/gunicorn_config.py
```

If it has any hardcoded paths to `/var/www/jalsarovar_demo/jalsarovar`, update them:

```bash
sudo nano /var/www/jalsarovar_demo/gunicorn_config.py
```

**Typical gunicorn_config.py should have:**

```python
import os
import multiprocessing

# Server socket
bind = "0.0.0.0:8001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = '/var/log/jalsarovar-demo/access.log'
errorlog = '/var/log/jalsarovar-demo/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'jalsarovar-demo'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = None
# certfile = None
```

---

### 4. Update Nginx Configuration (If Applicable)

**File**: `/etc/nginx/sites-available/jalsarovar-demo`

Usually Nginx doesn't need path changes for Flask apps since it proxies to the port, but check if there are any static file paths:

```bash
sudo nano /etc/nginx/sites-available/jalsarovar-demo
```

**If it has static file locations, update them:**

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name demo.jalsarovar.com;

    # Logging
    access_log /var/log/nginx/jalsarovar-demo-access.log;
    error_log /var/log/nginx/jalsarovar-demo-error.log;

    # OLD (if it exists):
    # root /var/www/jalsarovar_demo/jalsarovar;

    # NEW:
    # root /var/www/jalsarovar_demo;

    # Static files (if served by nginx)
    location /static {
        # OLD:
        # alias /var/www/jalsarovar_demo/jalsarovar/app/static;

        # NEW:
        alias /var/www/jalsarovar_demo/app/static;
        expires 30d;
    }

    # Proxy to Flask application
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### 5. Update Flask Migration Path

When running migrations, use the correct working directory:

```bash
# Navigate to the correct directory
cd /var/www/jalsarovar_demo

# Run migrations
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade
```

---

### 6. Update Any Backup Scripts

If you have backup scripts that reference paths, update them:

**File**: `/var/www/jalsarovar_demo/deployment/scripts/backup.sh` (if it exists)

Change any references from:
```bash
/var/www/jalsarovar_demo/jalsarovar
```

To:
```bash
/var/www/jalsarovar_demo
```

---

## Complete Setup Steps

After making all changes above:

### 1. Verify File Locations

```bash
# Check files are at root level
ls -la /var/www/jalsarovar_demo/ | grep -E "app.py|config.py|requirements.txt"

# Check app directory exists
ls -la /var/www/jalsarovar_demo/app/

# Check models directory
ls -la /var/www/jalsarovar_demo/app/models/

# Check ML models
ls -la /var/www/jalsarovar_demo/app/ml/models/
```

### 2. Create Virtual Environment (if not exists)

```bash
sudo -u jalsarovar-demo python3.11 -m venv /var/www/jalsarovar_demo/venv
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install --upgrade pip
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/pip install -r /var/www/jalsarovar_demo/requirements.txt
```

### 3. Set Correct Permissions

```bash
# Set ownership
sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo

# Set permissions for .env.production
sudo chmod 600 /var/www/jalsarovar_demo/.env.production

# Create required directories if they don't exist
sudo -u jalsarovar-demo mkdir -p /var/www/jalsarovar_demo/uploads
sudo -u jalsarovar-demo mkdir -p /var/www/jalsarovar_demo/logs
sudo -u jalsarovar-demo mkdir -p /var/log/jalsarovar-demo
```

### 4. Test Flask App

```bash
cd /var/www/jalsarovar_demo

# Test imports
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/python3 -c "
from app import create_app
app = create_app('production')
print('✓ App created successfully')
"

# Test database connection
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/python3 -c "
from app import create_app, db
app = create_app('production')
with app.app_context():
    db.engine.connect()
    print('✓ Database connection successful')
"
```

### 5. Run Database Migrations

```bash
cd /var/www/jalsarovar_demo
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade
```

### 6. Reload and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Restart nginx (if you modified nginx config)
sudo nginx -t
sudo systemctl reload nginx

# Start demo service
sudo systemctl start jalsarovar-demo

# Check status
sudo systemctl status jalsarovar-demo

# Follow logs
sudo journalctl -u jalsarovar-demo -f
```

### 7. Verify Application

```bash
# Test health endpoint
curl http://localhost:8001/health

# Expected output:
# {"status": "healthy", "service": "jal-sarovar"}

# Test from browser
# http://demo.jalsarovar.com
```

---

## Summary of Path Changes

| Component | Old Path | New Path |
|-----------|----------|----------|
| **Working Directory** | `/var/www/jalsarovar_demo/jalsarovar` | `/var/www/jalsarovar_demo` |
| **Environment File** | `/var/www/jalsarovar_demo/jalsarovar/.env.production` | `/var/www/jalsarovar_demo/.env.production` |
| **Gunicorn Config** | `/var/www/jalsarovar_demo/jalsarovar/gunicorn_config.py` | `/var/www/jalsarovar_demo/gunicorn_config.py` |
| **App Entry Point** | `/var/www/jalsarovar_demo/jalsarovar/app.py` | `/var/www/jalsarovar_demo/app.py` |
| **Static Files** | `/var/www/jalsarovar_demo/jalsarovar/app/static` | `/var/www/jalsarovar_demo/app/static` |
| **Uploads** | `/var/www/jalsarovar_demo/jalsarovar/uploads` | `/var/www/jalsarovar_demo/uploads` |
| **ML Models** | `/var/www/jalsarovar_demo/jalsarovar/app/ml/models` | `/var/www/jalsarovar_demo/app/ml/models` |

---

## Quick Reference Commands

```bash
# 1. Update systemd service
sudo nano /etc/systemd/system/jalsarovar-demo.service
# Change WorkingDirectory, EnvironmentFile, ExecStart paths

# 2. Create environment file
sudo nano /var/www/jalsarovar_demo/.env.production
# Add database credentials and config

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Run migrations
cd /var/www/jalsarovar_demo
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade

# 5. Start service
sudo systemctl start jalsarovar-demo

# 6. Check status
sudo systemctl status jalsarovar-demo

# 7. Test application
curl http://localhost:8001/health
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u jalsarovar-demo -n 50

# Common issues:
# 1. Wrong working directory - check systemd service file
# 2. Missing .env.production - create at /var/www/jalsarovar_demo/.env.production
# 3. Wrong permissions - run: sudo chown -R jalsarovar-demo:jalsarovar-demo /var/www/jalsarovar_demo
```

### Import Errors

```bash
# Ensure working directory is correct
cd /var/www/jalsarovar_demo

# Test imports
sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/python3 -c "from app.models import User; print('✓ Imports work')"
```

### Database Connection Errors

```bash
# Check .env.production exists and has correct values
cat /var/www/jalsarovar_demo/.env.production | grep DB_

# Test connection
PGPASSWORD=your-password psql -h localhost -U postgres -d jal_sarovar_demo -c "SELECT 1"
```

---

**Status**: All paths updated for flat directory structure

**Ready**: Yes, after making these changes the application should work from `/var/www/jalsarovar_demo/`
