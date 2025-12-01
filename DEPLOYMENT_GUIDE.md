# Jal Sarovar - Production Deployment Guide

Water Quality Monitoring and Management System

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Pre-deployment Checklist](#pre-deployment-checklist)
4. [Quick Deployment](#quick-deployment)
5. [Manual Deployment](#manual-deployment)
6. [Post-Deployment Configuration](#post-deployment-configuration)
7. [Security Hardening](#security-hardening)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)
10. [Backup and Recovery](#backup-and-recovery)

---

## Overview

Jal Sarovar is a comprehensive water quality monitoring and management system built with Flask and Python. This deployment guide covers production deployment on Ubuntu/Debian-based Linux servers.

### Key Features
- Voice Agent (IVR Notifications)
- Risk Prediction (Site Risk Assessment)
- WQI Calculator (Water Quality Index)
- ML Analytics (Anomaly Detection, Forecasting)
- Data Import/Export
- Intervention Tracking
- Residential Monitoring (Raspberry Pi integration)

---

## System Requirements

### Minimum Requirements
- **OS**: Ubuntu 20.04 LTS or Debian 11+ (64-bit)
- **RAM**: 4 GB (8 GB recommended)
- **Storage**: 20 GB free space (50 GB recommended)
- **CPU**: 2 cores (4 cores recommended)
- **Python**: 3.8 or higher

### Recommended Cloud Platforms
- AWS EC2 (t3.medium or larger)
- DigitalOcean Droplet (4GB RAM or larger)
- Google Cloud Compute Engine (e2-medium or larger)
- Azure Virtual Machine (B2s or larger)

### Network Requirements
- Open ports: 80 (HTTP), 443 (HTTPS)
- Stable internet connection
- Domain name (optional but recommended)

---

## Pre-deployment Checklist

Before deploying, ensure you have:

- [ ] Root/sudo access to the server
- [ ] Fresh Ubuntu/Debian installation with latest updates
- [ ] SSH access configured
- [ ] Domain name pointed to server IP (optional)
- [ ] SSL certificate (Let's Encrypt recommended)
- [ ] Backup strategy planned
- [ ] Database credentials ready (if using PostgreSQL)

---

## Quick Deployment

The fastest way to deploy Jal Sarovar is using the automated deployment script:

### Step 1: Upload Files to Server

```bash
# On your local machine
scp -r jalsarovar_RELEASE root@your-server-ip:/tmp/

# SSH into your server
ssh root@your-server-ip
```

### Step 2: Run Deployment Script

```bash
cd /tmp/jalsarovar_RELEASE
sudo bash deploy.sh
```

The script will:
1. Install system dependencies
2. Create application directory structure
3. Deploy application files
4. Setup Python virtual environment
5. Import database
6. Configure Nginx
7. Setup Supervisor for process management
8. Configure automatic backups
9. Run health checks

### Step 3: Access Application

After deployment completes, access your application at:

```
http://your-server-ip/
```

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

**⚠️ Change the admin password immediately after first login!**

---

## Manual Deployment

If you prefer manual deployment or need to customize the process:

### 1. Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev \
    build-essential nginx postgresql postgresql-contrib \
    libpq-dev supervisor sqlite3 gzip curl
```

### 2. Create Application Directory

```bash
sudo mkdir -p /var/www/jalsarovar
sudo mkdir -p /var/www/jalsarovar/{instance,logs,uploads,backups}
cd /var/www/jalsarovar
```

### 3. Copy Application Files

```bash
# Copy from your RELEASE directory
sudo cp -r /tmp/jalsarovar_RELEASE/* /var/www/jalsarovar/
```

### 4. Setup Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Import Database

```bash
gunzip -c database/jalsarovar_production.sql.gz | \
    sqlite3 instance/jalsarovar.db
```

### 6. Create Production .env File

```bash
cat > .env <<EOF
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=sqlite:///$(pwd)/instance/jalsarovar.db
DEBUG=False
ML_MODELS_PATH=app/ml/models
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=$(pwd)/uploads
LOG_LEVEL=INFO
EOF
```

### 7. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/jalsarovar
```

Add the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/jalsarovar/app/static;
        expires 30d;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/jalsarovar /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8. Configure Supervisor

```bash
sudo nano /etc/supervisor/conf.d/jalsarovar.conf
```

Add:

```ini
[program:jalsarovar]
command=/var/www/jalsarovar/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --threads 2 --timeout 60 app:app
directory=/var/www/jalsarovar
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/www/jalsarovar/logs/error.log
stdout_logfile=/var/www/jalsarovar/logs/access.log
```

Start the application:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start jalsarovar
```

### 9. Set Permissions

```bash
sudo chown -R www-data:www-data /var/www/jalsarovar
sudo chmod 755 /var/www/jalsarovar
```

---

## Post-Deployment Configuration

### 1. Setup SSL with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. Configure Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

### 3. Change Default Admin Password

1. Login at http://your-domain.com/
2. Go to User Settings
3. Change password to a strong password
4. Enable two-factor authentication (if available)

### 4. Configure Email Notifications (Optional)

Edit `.env` file:

```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### 5. Setup Database Backups

The deployment script creates an automatic backup cron job. Verify:

```bash
crontab -u www-data -l
```

Manual backup:

```bash
sudo -u www-data /var/www/jalsarovar/backup.sh
```

---

## Security Hardening

### 1. Secure SSH Access

```bash
# Disable root login
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no

# Use SSH keys only
# Set: PasswordAuthentication no

sudo systemctl restart sshd
```

### 2. Enable Fail2Ban

```bash
sudo apt-get install fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Regular Updates

```bash
# Create update script
cat > /etc/cron.weekly/system-updates <<'EOF'
#!/bin/bash
apt-get update
apt-get upgrade -y
apt-get autoremove -y
EOF

chmod +x /etc/cron.weekly/system-updates
```

### 4. Database Encryption

For PostgreSQL production deployments:

```bash
# Enable SSL connections
sudo nano /etc/postgresql/*/main/postgresql.conf
# Set: ssl = on
```

### 5. Application Security Headers

Add to Nginx configuration:

```nginx
add_header X-Frame-Options "SAMEORIGIN";
add_header X-Content-Type-Options "nosniff";
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000";
```

---

## Monitoring and Maintenance

### Application Monitoring

**Check Application Status:**
```bash
sudo supervisorctl status jalsarovar
```

**View Application Logs:**
```bash
tail -f /var/www/jalsarovar/logs/error.log
tail -f /var/www/jalsarovar/logs/access.log
```

**Check Nginx Logs:**
```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Performance Monitoring

**Install htop:**
```bash
sudo apt-get install htop
htop
```

**Monitor Disk Usage:**
```bash
df -h
du -sh /var/www/jalsarovar/*
```

**Check Database Size:**
```bash
ls -lh /var/www/jalsarovar/instance/jalsarovar.db
```

### Restart Services

**Restart Application:**
```bash
sudo supervisorctl restart jalsarovar
```

**Restart Nginx:**
```bash
sudo systemctl restart nginx
```

**Restart All Services:**
```bash
sudo supervisorctl restart all
sudo systemctl restart nginx
```

---

## Troubleshooting

### Application Won't Start

**Check logs:**
```bash
tail -100 /var/www/jalsarovar/logs/error.log
```

**Check supervisor status:**
```bash
sudo supervisorctl status
```

**Common issues:**
- Missing Python dependencies: `pip install -r requirements.txt`
- Database file permissions: `chmod 660 instance/jalsarovar.db`
- Port already in use: `sudo lsof -i :8000`

### 502 Bad Gateway

This usually means Gunicorn isn't running:

```bash
sudo supervisorctl status jalsarovar
sudo supervisorctl restart jalsarovar
```

### Database Locked Error

```bash
# Check for active connections
sudo lsof /var/www/jalsarovar/instance/jalsarovar.db

# Kill blocking processes if needed
sudo supervisorctl restart jalsarovar
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Reduce Gunicorn workers
# Edit: /etc/supervisor/conf.d/jalsarovar.conf
# Change --workers to 2
sudo supervisorctl restart jalsarovar
```

### Slow Response Times

```bash
# Enable database optimization
sqlite3 /var/www/jalsarovar/instance/jalsarovar.db "VACUUM;"
sqlite3 /var/www/jalsarovar/instance/jalsarovar.db "ANALYZE;"
```

---

## Backup and Recovery

### Automated Backups

Backups run daily at 2 AM via cron:

```bash
# Check cron jobs
crontab -u www-data -l

# Manual backup
sudo -u www-data /var/www/jalsarovar/backup.sh
```

### Manual Database Backup

```bash
# Backup database
sqlite3 /var/www/jalsarovar/instance/jalsarovar.db ".dump" | \
    gzip > backup_$(date +%Y%m%d).sql.gz

# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz \
    /var/www/jalsarovar/uploads/
```

### Restore from Backup

```bash
# Stop application
sudo supervisorctl stop jalsarovar

# Restore database
gunzip -c backup_20250101.sql.gz | \
    sqlite3 /var/www/jalsarovar/instance/jalsarovar.db

# Restore uploads
tar -xzf uploads_backup_20250101.tar.gz -C /

# Start application
sudo supervisorctl start jalsarovar
```

### Disaster Recovery

For complete system failure:

1. Setup new server with same OS
2. Install Jal Sarovar using deployment script
3. Restore database from latest backup
4. Restore uploads directory
5. Update DNS if IP changed
6. Re-issue SSL certificate

---

## Support and Documentation

For additional help, see:
- `README.md` - Full functional specifications
- `QUICKSTART.md` - Quick start guide
- Application logs: `/var/www/jalsarovar/logs/`

---

## License

Jal Sarovar - Water Quality Monitoring and Management System
Version: 1.0.0
Last Updated: December 1, 2025
