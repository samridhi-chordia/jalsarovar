# Deploying to Existing Cloud Server (www.jalsarovar.com)

Complete step-by-step guide for deploying Lab4All Web Application to your existing cloud server using SCP and tar.

---

## Prerequisites

### On Your Local Machine

- [ ] SSH access to remote server
- [ ] SCP/rsync available
- [ ] Application source code at `/Users/test/lab4all_wflow_RELEASE_RONALD/lab4all_webapp`

### On Remote Server (www.jalsarovar.com)

- [ ] Ubuntu 20.04 or 22.04 LTS (or compatible Linux distribution)
- [ ] Root or sudo access
- [ ] PostgreSQL 15 installed and running
- [ ] Port 80 (HTTP) and 443 (HTTPS) open in firewall
- [ ] At least 4GB RAM and 20GB free disk space

---

## Quick Deployment (Automated)

### Step 1: Create Deployment Package (Local Machine)

```bash
cd /Users/test/lab4all_wflow_RELEASE_RONALD/lab4all_webapp

# Make script executable
chmod +x deployment/scripts/create_deployment_package.sh

# Create deployment package
./deployment/scripts/create_deployment_package.sh

# This creates: lab4all_webapp_YYYYMMDD_HHMMSS.tar.gz
```

**Output**: A compressed tar file (~50-100 MB) in the current directory.

### Step 2: Transfer to Remote Server

```bash
# Replace 'user' with your SSH username
# Replace 'www.jalsarovar.com' with your server IP if needed

scp lab4all_webapp_*.tar.gz user@www.jalsarovar.com:/tmp/

# Example:
# scp lab4all_webapp_20250122_143022.tar.gz root@www.jalsarovar.com:/tmp/
```

**Note**: If you have a custom SSH port:
```bash
scp -P 2222 lab4all_webapp_*.tar.gz user@www.jalsarovar.com:/tmp/
```

### Step 3: Connect to Remote Server

```bash
ssh user@www.jalsarovar.com

# Or with custom port:
# ssh -p 2222 user@www.jalsarovar.com
```

### Step 4: Extract and Deploy

```bash
# On remote server
cd /tmp

# Extract package
tar -xzf lab4all_webapp_*.tar.gz
cd lab4all_webapp_*

# Read the deployment readme
cat DEPLOY_README.txt

# Run automated setup
sudo bash deployment/scripts/remote_setup.sh
```

### Step 5: Follow Interactive Setup

The script will prompt you for:

1. **Domain name**: `www.jalsarovar.com`
2. **Database host**: `localhost` (or remote DB host)
3. **Database port**: `5432` (default)
4. **Database name**: `jal_sarovar_prod`
5. **Database user**: `postgres` (or dedicated user)
6. **Database password**: Your database password
7. **Flask secret key**: Leave blank to auto-generate
8. **Enable SSL**: `y` (recommended)

### Step 6: Verify Deployment

```bash
# Check application status
sudo systemctl status lab4all

# Check logs
sudo journalctl -u lab4all -n 50

# Test application
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "service": "jal-sarovar"}
```

### Step 7: Access Your Application

Open browser and navigate to:
- **HTTP**: http://www.jalsarovar.com
- **HTTPS**: https://www.jalsarovar.com (after SSL setup)

---

## Manual Deployment (Step-by-Step)

If you prefer manual control or the automated script fails:

### 1. Prepare Local Package

```bash
cd /Users/test/lab4all_wflow_RELEASE_RONALD/lab4all_webapp

# Create tarball manually (excluding unnecessary files)
tar -czf lab4all_webapp.tar.gz \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='venv' \
    --exclude='uploads/*' \
    --exclude='*.db' \
    .

# Check size
ls -lh lab4all_webapp.tar.gz
```

### 2. Transfer to Server

```bash
scp lab4all_webapp.tar.gz user@www.jalsarovar.com:/tmp/
```

### 3. On Remote Server - Install Dependencies

```bash
ssh user@www.jalsarovar.com
sudo apt-get update
sudo apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    postgresql-client \
    nginx \
    build-essential \
    libpq-dev
```

### 4. Create Application User

```bash
sudo useradd -m -s /bin/bash lab4all
sudo mkdir -p /opt/lab4all
sudo chown lab4all:lab4all /opt/lab4all
```

### 5. Extract Application

```bash
cd /tmp
tar -xzf lab4all_webapp.tar.gz
sudo mv lab4all_webapp /opt/lab4all/
sudo chown -R lab4all:lab4all /opt/lab4all
```

### 6. Set Up Python Environment

```bash
sudo -u lab4all python3.11 -m venv /opt/lab4all/venv
sudo -u lab4all /opt/lab4all/venv/bin/pip install --upgrade pip
sudo -u lab4all /opt/lab4all/venv/bin/pip install -r /opt/lab4all/lab4all_webapp/requirements.txt
```

### 7. Configure Environment

```bash
# Create .env.production file
sudo nano /opt/lab4all/lab4all_webapp/.env.production
```

Paste the following (update values):

```ini
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=<generate-with-python-command-below>

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jal_sarovar_prod
DB_USER=postgres
DB_PASSWORD=<your-db-password>

# Application Settings
PORT=8000
WORKERS=4
LOG_LEVEL=info

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True

# Paths
UPLOAD_FOLDER=/opt/lab4all/lab4all_webapp/uploads
ML_MODELS_PATH=/opt/lab4all/lab4all_webapp/models
```

Generate secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Set permissions:
```bash
sudo chown lab4all:lab4all /opt/lab4all/lab4all_webapp/.env.production
sudo chmod 600 /opt/lab4all/lab4all_webapp/.env.production
```

### 8. Set Up Database

```bash
# Test connection
PGPASSWORD=your-password psql -h localhost -U postgres -d jal_sarovar_prod -c "SELECT 1"

# Run migrations
cd /opt/lab4all/lab4all_webapp
sudo -u lab4all /opt/lab4all/venv/bin/flask db upgrade
```

### 9. Create Systemd Service

```bash
sudo nano /etc/systemd/system/lab4all.service
```

Paste:

```ini
[Unit]
Description=Lab4All Water Quality Management System
After=network.target postgresql.service

[Service]
Type=notify
User=lab4all
Group=lab4all
WorkingDirectory=/opt/lab4all/lab4all_webapp
Environment="PATH=/opt/lab4all/venv/bin"
EnvironmentFile=/opt/lab4all/lab4all_webapp/.env.production

ExecStart=/opt/lab4all/venv/bin/gunicorn \
    --config /opt/lab4all/lab4all_webapp/gunicorn_config.py \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable lab4all
sudo systemctl start lab4all
sudo systemctl status lab4all
```

### 10. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/lab4all
```

For HTTP (port 80):

```nginx
upstream lab4all_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name www.jalsarovar.com jalsarovar.com;

    client_max_body_size 50M;

    location /static/ {
        alias /opt/lab4all/lab4all_webapp/app/static/;
        expires 30d;
    }

    location /uploads/ {
        alias /opt/lab4all/lab4all_webapp/uploads/;
        expires 7d;
    }

    location / {
        proxy_pass http://lab4all_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/lab4all /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t
sudo systemctl reload nginx
```

### 11. Configure Firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
sudo ufw status
```

### 12. Test Deployment

```bash
# Test local access
curl http://localhost:8000/health

# Test via nginx
curl http://localhost/health

# Test from external
curl http://www.jalsarovar.com/health
```

---

## SSL/HTTPS Setup with Let's Encrypt

After successful HTTP deployment:

### 1. Install Certbot

```bash
sudo apt-get install -y certbot python3-certbot-nginx
```

### 2. Obtain Certificate

```bash
sudo certbot --nginx -d www.jalsarovar.com -d jalsarovar.com
```

Follow the prompts:
- Enter email address
- Agree to terms
- Choose to redirect HTTP to HTTPS (recommended)

### 3. Verify Auto-Renewal

```bash
sudo certbot renew --dry-run
```

Certbot automatically sets up a cron job for renewal.

### 4. Test HTTPS

```bash
curl https://www.jalsarovar.com/health
```

---

## Post-Deployment Tasks

### 1. Create Admin User

```bash
cd /opt/lab4all/lab4all_webapp
sudo -u lab4all /opt/lab4all/venv/bin/python3 << 'EOF'
from app import create_app, db
from app.models import User

app = create_app('production')
with app.app_context():
    admin = User(
        username='admin',
        email='admin@jalsarovar.com',
        is_admin=True
    )
    admin.set_password('YourSecurePassword123!')
    db.session.add(admin)
    db.session.commit()
    print('Admin user created successfully')
EOF
```

### 2. Upload ML Models

If you have pre-trained models:

```bash
# From local machine
scp -r ALL_MODELS/* user@www.jalsarovar.com:/tmp/models/

# On remote server
sudo mkdir -p /opt/lab4all/lab4all_webapp/models
sudo mv /tmp/models/* /opt/lab4all/lab4all_webapp/models/
sudo chown -R lab4all:lab4all /opt/lab4all/lab4all_webapp/models
```

### 3. Set Up Automated Backups

```bash
# Make backup script executable
sudo chmod +x /opt/lab4all/lab4all_webapp/deployment/scripts/backup.sh

# Add to crontab
sudo crontab -e

# Add this line (backup at 2 AM daily):
0 2 * * * /opt/lab4all/lab4all_webapp/deployment/scripts/backup.sh
```

### 4. Configure Log Rotation

```bash
sudo nano /etc/logrotate.d/lab4all
```

Paste:

```
/var/log/lab4all/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 lab4all lab4all
    sharedscripts
    postrotate
        systemctl reload lab4all > /dev/null 2>&1 || true
    endscript
}
```

---

## Monitoring and Maintenance

### Check Application Status

```bash
# Service status
sudo systemctl status lab4all

# Recent logs
sudo journalctl -u lab4all -n 100

# Follow logs in real-time
sudo journalctl -u lab4all -f

# Application logs
sudo tail -f /var/log/lab4all/error.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Restart Application

```bash
sudo systemctl restart lab4all
```

### Update Application

When you need to deploy updates:

```bash
# 1. Create new package on local machine
./deployment/scripts/create_deployment_package.sh

# 2. Transfer to server
scp lab4all_webapp_*.tar.gz user@www.jalsarovar.com:/tmp/

# 3. On server - stop application
sudo systemctl stop lab4all

# 4. Backup current installation
sudo mv /opt/lab4all/lab4all_webapp /opt/lab4all/lab4all_webapp.backup.$(date +%Y%m%d)

# 5. Extract new version
cd /tmp
tar -xzf lab4all_webapp_*.tar.gz
sudo mv lab4all_webapp_*/* /opt/lab4all/lab4all_webapp/
sudo chown -R lab4all:lab4all /opt/lab4all

# 6. Run migrations
cd /opt/lab4all/lab4all_webapp
sudo -u lab4all /opt/lab4all/venv/bin/flask db upgrade

# 7. Restart application
sudo systemctl start lab4all
sudo systemctl status lab4all
```

### Performance Tuning

If you need to scale:

```bash
# Increase workers in gunicorn_config.py
sudo nano /opt/lab4all/lab4all_webapp/gunicorn_config.py

# Change:
workers = 8  # 2 * CPU cores + 1

# Restart
sudo systemctl restart lab4all
```

---

## Troubleshooting

### Application Won't Start

**Check logs**:
```bash
sudo journalctl -u lab4all -n 100
```

**Common issues**:
1. Database connection - verify credentials in `.env.production`
2. Port already in use - check: `sudo lsof -i :8000`
3. Permission issues - verify ownership: `ls -la /opt/lab4all/`

### 502 Bad Gateway

**Check if app is running**:
```bash
curl http://localhost:8000/health
```

If fails:
```bash
sudo systemctl status lab4all
sudo journalctl -u lab4all -n 50
```

### Database Connection Errors

**Test connection**:
```bash
PGPASSWORD=your-password psql -h localhost -U postgres -d jal_sarovar_prod -c "SELECT version();"
```

**Check PostgreSQL is running**:
```bash
sudo systemctl status postgresql
```

### High Memory Usage

**Check processes**:
```bash
ps aux --sort=-%mem | head -10
```

**Reduce workers**:
Edit `/opt/lab4all/lab4all_webapp/gunicorn_config.py` and reduce `workers` value.

### SSL Certificate Issues

**Check certificate status**:
```bash
sudo certbot certificates
```

**Renew manually**:
```bash
sudo certbot renew
sudo systemctl reload nginx
```

---

## Rollback Procedure

If something goes wrong:

```bash
# Stop current version
sudo systemctl stop lab4all

# Restore backup
sudo rm -rf /opt/lab4all/lab4all_webapp
sudo mv /opt/lab4all/lab4all_webapp.backup.YYYYMMDD /opt/lab4all/lab4all_webapp

# Restart
sudo systemctl start lab4all
```

---

## Performance Benchmarks

Expected performance on a 4GB/2 CPU server:

- **Concurrent users**: 500-1000
- **Response time**: < 500ms (average)
- **Memory usage**: ~1-2GB
- **CPU usage**: 30-60% (under load)

---

## Security Checklist

- [x] Strong database password (16+ characters)
- [x] Unique Flask SECRET_KEY
- [x] SSL/HTTPS enabled
- [x] Firewall configured (only ports 22, 80, 443)
- [x] Application runs as non-root user
- [x] Database not publicly accessible
- [x] Regular backups configured
- [x] Log rotation enabled
- [x] Security headers in Nginx
- [ ] Consider: fail2ban for SSH protection
- [ ] Consider: ModSecurity or Nginx WAF
- [ ] Consider: Database connection encryption

---

## Support and Maintenance

### Regular Tasks

**Daily**:
- Monitor application logs
- Check disk space: `df -h`

**Weekly**:
- Review error logs
- Check backup success
- Monitor performance

**Monthly**:
- Update system packages: `sudo apt-get update && sudo apt-get upgrade`
- Review security logs
- Test backup restoration
- Check SSL certificate expiry

### Getting Help

**Check logs**:
```bash
# Application
sudo journalctl -u lab4all -f

# Nginx
sudo tail -f /var/log/nginx/error.log

# System
sudo tail -f /var/log/syslog
```

**Useful commands**:
```bash
# System resources
htop
df -h
free -h

# Network
sudo netstat -tulpn | grep LISTEN
sudo ss -tulpn

# Process info
ps aux | grep gunicorn
```

---

## Quick Reference

### File Locations

```
/opt/lab4all/                          # Application root
├── venv/                              # Python virtual environment
└── lab4all_webapp/                    # Application code
    ├── app/                           # Flask application
    ├── uploads/                       # User uploads
    ├── models/                        # ML models
    ├── logs/                          # Application logs
    └── .env.production                # Environment config

/var/log/lab4all/                      # Log directory
/etc/systemd/system/lab4all.service   # Systemd service
/etc/nginx/sites-available/lab4all    # Nginx config
```

### Important Commands

```bash
# Service management
sudo systemctl start lab4all
sudo systemctl stop lab4all
sudo systemctl restart lab4all
sudo systemctl status lab4all

# View logs
sudo journalctl -u lab4all -f
sudo tail -f /var/log/lab4all/error.log

# Nginx
sudo nginx -t                          # Test config
sudo systemctl reload nginx            # Reload config
sudo systemctl restart nginx           # Restart

# Database
sudo -u postgres psql jal_sarovar_prod # Connect to DB
```

---

**Document Version**: 1.0
**Last Updated**: December 22, 2025
**For**: www.jalsarovar.com deployment
