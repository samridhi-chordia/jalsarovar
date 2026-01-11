# Jal Sarovar - Production Deployment Guide
# Water Quality Management System with OAuth & 10-Role Permission System

**Last Updated:** December 28, 2025
**Version:** 1.0.0 (Production Ready)
**Implementation:** Weeks 1-8 Complete

---

## Table of Contents

1. [Overview](#overview)
2. [System Requirements](#system-requirements)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Configuration](#configuration)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

---

## Overview

This guide covers the complete production deployment of the Jal Sarovar Water Quality Management System, including:

- **Authentication System**: OAuth (Google) + Traditional Email/Password
- **10-Role Permission System**: From Viewer to Admin
- **Email Verification**: Secure account activation
- **Role Approval Workflow**: Admin-managed role upgrades
- **Rate Limiting**: Redis-backed protection against abuse
- **Health Monitoring**: Automated checks and alerting
- **Database Optimization**: Indexed for performance

---

## System Requirements

### Minimum Hardware
- **CPU**: 2 cores (4 recommended)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 20GB SSD (50GB+ recommended for data growth)
- **Network**: Static IP, domain name

### Software Requirements
- **OS**: Ubuntu 20.04 LTS or newer
- **Python**: 3.8+
- **PostgreSQL**: 12+
- **Nginx**: 1.18+
- **Redis**: 5.0+
- **Supervisor**: 4.1+

### External Services
- **Google Cloud Console**: OAuth credentials
- **Email Provider**: SendGrid (recommended) or Gmail SMTP
- **SSL Certificate**: Let's Encrypt (free)
- **Domain Name**: Registered and configured

---

## Pre-Deployment Checklist

### 1. Infrastructure Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-venv python3-pip postgresql redis-server \
    nginx supervisor git curl

# Install certbot for SSL
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Database Setup

```bash
# Create database and user
sudo -u postgres psql
```

```sql
CREATE DATABASE jal_sarovar_prod;
CREATE USER jal_user WITH ENCRYPTED PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE jal_sarovar_prod TO jal_user;
\q
```

### 3. Application Setup

```bash
# Create application directory
sudo mkdir -p /var/www/jalsarovar
sudo chown www-data:www-data /var/www/jalsarovar

# Clone repository (or copy files)
cd /var/www/jalsarovar
# git clone your-repository-url .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
# Copy example environment file
cp .env.production.example .env

# Edit with your production values
nano .env
```

**Critical Variables to Set:**
- `SECRET_KEY` - Generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `DB_PASSWORD` - Your PostgreSQL password
- `GOOGLE_CLIENT_ID` - From Google Cloud Console
- `GOOGLE_CLIENT_SECRET` - From Google Cloud Console
- `MAIL_PASSWORD` - SendGrid API key or Gmail app password
- `SITE_URL` - Your production domain (e.g., `https://jalsarovar.com`)

### 5. File Permissions

```bash
# Set correct ownership
sudo chown -R www-data:www-data /var/www/jalsarovar

# Set correct permissions
sudo chmod 755 /var/www/jalsarovar
sudo chmod -R 755 /var/www/jalsarovar/app
sudo chmod 640 /var/www/jalsarovar/.env

# Create directories
sudo mkdir -p /var/www/jalsarovar/{uploads,backups,logs}
sudo chown www-data:www-data /var/www/jalsarovar/{uploads,backups,logs}
```

---

## Step-by-Step Deployment

### Step 1: Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable "Google+ API"
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized JavaScript origins: `https://yourdomain.com`
   - Authorized redirect URIs: `https://yourdomain.com/auth/google/callback`
5. Copy Client ID and Client Secret to `.env`

### Step 2: Email Service Setup

**Option A: SendGrid (Recommended)**

1. Sign up at [SendGrid](https://sendgrid.com/)
2. Create API key with "Mail Send" permission
3. Configure DNS records (SPF, DKIM, DMARC)
4. Update `.env`:
   ```bash
   MAIL_SERVER=smtp.sendgrid.net
   MAIL_PORT=587
   MAIL_USERNAME=apikey
   MAIL_PASSWORD=SG.your-api-key-here
   ```

**Option B: Gmail (Development Only)**

1. Enable 2-Factor Authentication on Gmail
2. Generate app password at: https://myaccount.google.com/apppasswords
3. Update `.env`:
   ```bash
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

### Step 3: Database Migration

```bash
cd /var/www/jalsarovar
source venv/bin/activate

# Run migrations
export FLASK_APP=app.py
flask db upgrade

# Verify database
python3 -c "
from app import create_app, db
app = create_app('production')
with app.app_context():
    db.engine.connect()
    print('✓ Database connected successfully')
"
```

### Step 4: SSL Certificate

```bash
# Obtain SSL certificate from Let's Encrypt
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Step 5: Nginx Configuration

```bash
# Copy production config
sudo cp /var/www/jalsarovar/nginx-production.conf /etc/nginx/sites-available/jalsarovar

# Enable site
sudo ln -sf /etc/nginx/sites-available/jalsarovar /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Step 6: Supervisor Configuration

```bash
# Supervisor config should already exist at:
# /etc/supervisor/conf.d/jalsarovar.conf

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start application
sudo supervisorctl start jalsarovar
```

### Step 7: Monitoring Setup

```bash
# Run monitoring setup script
sudo chmod +x /var/www/jalsarovar/monitoring-setup.sh
sudo /var/www/jalsarovar/monitoring-setup.sh
```

This configures:
- Log rotation (30 days)
- Health checks (every 5 minutes)
- Database backups (daily at 2 AM)
- Status dashboard

### Step 8: Deployment Script

```bash
# Make deployment script executable
sudo chmod +x /var/www/jalsarovar/deploy.sh

# Run initial deployment
sudo /var/www/jalsarovar/deploy.sh production
```

---

## Configuration

### Production Environment Variables

```bash
# Application
FLASK_ENV=production
DEBUG=False
SECRET_KEY=<64-character-random-string>

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=jal_sarovar_prod
DB_USER=jal_user
DB_PASSWORD=<secure-password>

# Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# OAuth
GOOGLE_CLIENT_ID=<production-client-id>
GOOGLE_CLIENT_SECRET=<production-secret>
OAUTHLIB_INSECURE_TRANSPORT=0

# Email
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=<sendgrid-api-key>
MAIL_DEFAULT_SENDER=noreply@yourdomain.com

# Site URL
SITE_URL=https://yourdomain.com
```

### Redis Configuration

Redis is already installed and configured. Verify:

```bash
redis-cli ping
# Should return: PONG

# Check memory usage
redis-cli INFO memory | grep used_memory_human
```

### Database Optimization

Indexes are already created. Verify:

```bash
sudo -u postgres psql -d jal_sarovar_prod -c "\di"
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable

# Verify
sudo ufw status
```

### 2. Fail2Ban (Optional but Recommended)

```bash
# Install
sudo apt install -y fail2ban

# Configure for Nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Edit to enable nginx-limit-req jail
sudo nano /etc/fail2ban/jail.local
```

Add:
```ini
[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/jalsarovar-error.log
```

```bash
# Restart fail2ban
sudo systemctl restart fail2ban
```

### 3. Database Security

```bash
# Edit PostgreSQL config
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Ensure only local connections allowed:
```
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
```

### 4. Application Security Checklist

- ✅ SESSION_COOKIE_SECURE=True
- ✅ Rate limiting active (Flask-Limiter + Redis)
- ✅ HTTPS enforced (Nginx redirect)
- ✅ Security headers configured
- ✅ File upload restrictions (50MB max)
- ✅ CSRF protection (inherent in Flask)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ XSS protection (Jinja2 auto-escaping)

---

## Monitoring & Maintenance

### Health Checks

**Endpoint:** https://yourdomain.com/health

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "jal-sarovar",
  "timestamp": "2025-12-28T10:09:29.793452",
  "database": "connected",
  "redis": "connected"
}
```

**Automated Monitoring:**
```bash
# Health check runs every 5 minutes via cron
# View logs:
tail -f /var/log/jalsarovar-health.log
```

### Status Dashboard

```bash
# View system status
/var/www/jalsarovar/scripts/status_dashboard.sh
```

### Log Files

```bash
# Application logs
tail -f /var/www/jalsarovar/logs/error.log
tail -f /var/www/jalsarovar/logs/access.log

# Nginx logs
tail -f /var/log/nginx/jalsarovar-error.log
tail -f /var/log/nginx/jalsarovar-access.log

# Supervisor logs
sudo supervisorctl tail jalsarovar stderr

# Health check logs
tail -f /var/log/jalsarovar-health.log

# Backup logs
tail -f /var/log/jalsarovar-backup.log
```

### Database Backups

**Manual Backup:**
```bash
/var/www/jalsarovar/scripts/db_backup.sh
```

**Automated:** Daily at 2 AM via cron

**Backup Location:** `/var/www/jalsarovar/backups/`

**Retention:** 30 days

**Restore Backup:**
```bash
cd /var/www/jalsarovar/backups
gunzip jalsarovar_backup_YYYYMMDD_HHMMSS.sql.gz
sudo -u postgres psql jal_sarovar_prod < jalsarovar_backup_YYYYMMDD_HHMMSS.sql
```

### Updating Application

```bash
# Use deployment script
sudo /var/www/jalsarovar/deploy.sh production
```

This script:
1. Creates database backup
2. Pulls latest code (if Git configured)
3. Installs/updates dependencies
4. Runs database migrations
5. Tests configuration
6. Restarts application
7. Verifies health

---

## Troubleshooting

### Application Won't Start

**Check supervisor status:**
```bash
sudo supervisorctl status jalsarovar
```

**Check logs for errors:**
```bash
sudo supervisorctl tail jalsarovar stderr
```

**Common issues:**
- Permission denied: `sudo chown -R www-data:www-data /var/www/jalsarovar`
- Database connection failed: Check `.env` DB_* variables
- Redis connection failed: `sudo systemctl start redis-server`

### Email Not Sending

**Test SMTP connection:**
```bash
cd /var/www/jalsarovar && source venv/bin/activate
python3 << EOF
from app import create_app, mail
from flask_mail import Message

app = create_app('production')
with app.app_context():
    msg = Message('Test', recipients=['your-email@example.com'], body='Test email')
    try:
        mail.send(msg)
        print('✓ Email sent successfully')
    except Exception as e:
        print(f'✗ Error: {e}')
EOF
```

**Common issues:**
- SMTP credentials incorrect
- Email provider blocking
- Missing DNS records (SPF, DKIM)

### High Database CPU

**Check active queries:**
```bash
sudo -u postgres psql -d jal_sarovar_prod -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"
```

**Analyze slow queries:**
```bash
# Enable slow query log
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Add:
```
log_min_duration_statement = 1000  # Log queries > 1 second
```

### Redis Memory Issues

**Check memory usage:**
```bash
redis-cli INFO memory
```

**Set max memory:**
```bash
sudo nano /etc/redis/redis.conf
```

Add:
```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

### Rate Limiting Too Aggressive

**Adjust limits in nginx:**
```bash
sudo nano /etc/nginx/sites-available/jalsarovar
```

Modify rate limit zones:
```nginx
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=20r/m;  # Increase from 10r/m
```

---

## Rollback Procedures

### Quick Rollback

```bash
# Stop application
sudo supervisorctl stop jalsarovar

# Restore database backup
cd /var/www/jalsarovar/backups
gunzip jalsarovar_backup_<timestamp>.sql.gz
sudo -u postgres psql jal_sarovar_prod < jalsarovar_backup_<timestamp>.sql

# Revert code (if using Git)
cd /var/www/jalsarovar
git checkout <previous-commit-hash>

# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start application
sudo supervisorctl start jalsarovar
```

### Emergency Stop

```bash
# Stop application immediately
sudo supervisorctl stop jalsarovar

# Disable site in Nginx
sudo rm /etc/nginx/sites-enabled/jalsarovar
sudo systemctl reload nginx
```

---

## Performance Tuning

### Gunicorn Workers

Edit `/etc/supervisor/conf.d/jalsarovar.conf`:

```ini
# Formula: (2 x CPU cores) + 1
command=/var/www/jalsarovar/venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 9 --threads 2 ...
```

### Database Connection Pool

In `.env`:
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

### Nginx Caching

Add to nginx config:
```nginx
# Cache zone
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=jalsarovar:10m max_size=1g inactive=60m;

# In location block
proxy_cache jalsarovar;
proxy_cache_valid 200 10m;
```

---

## Success Metrics

After deployment, verify these metrics:

- ✅ Health check: `https://yourdomain.com/health` returns 200
- ✅ Login works (both email and OAuth)
- ✅ Email verification sends
- ✅ Role approval workflow functions
- ✅ Rate limiting enforces (test with rapid requests)
- ✅ SSL/TLS A+ rating: https://www.ssllabs.com/ssltest/
- ✅ All 10 roles work correctly
- ✅ Database backups running daily
- ✅ Logs rotating properly

---

## Support & Resources

- **Application Logs:** `/var/www/jalsarovar/logs/`
- **Status Dashboard:** `/var/www/jalsarovar/scripts/status_dashboard.sh`
- **Week 7 Security Report:** `/var/www/jalsarovar/WEEK7_SECURITY_TESTING_REPORT.md`
- **Environment Example:** `/var/www/jalsarovar/.env.production.example`

---

## Conclusion

Your Jal Sarovar Water Quality Management System is now production-ready with:

- ✅ Secure authentication (OAuth + Email/Password)
- ✅ 10-role permission system with approval workflow
- ✅ Email verification and password reset
- ✅ Rate limiting (Redis-backed)
- ✅ Automated monitoring and backups
- ✅ Production-grade security headers
- ✅ Optimized database with indexes
- ✅ Health check monitoring

**Next Steps:**
1. Monitor application logs for first 48 hours
2. Set up error alerting (Sentry recommended)
3. Configure DNS records for email deliverability
4. Perform load testing
5. User acceptance testing
6. Create admin user and test role approvals

---

**Last Updated:** December 28, 2025
**Deployed By:** Jal Sarovar Development Team
**Production Status:** ✅ READY
