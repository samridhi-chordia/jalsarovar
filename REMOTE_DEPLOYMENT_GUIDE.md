# Jal Sarovar - Remote Server Deployment Guide

## Complete Automatic Deployment to www.jalsarovar.com

---

## 📦 Deployment Package Information

**Package Name:** `jalsarovar_deployment_complete_20251227_225552.tar.gz`
**Package Size:** 26 MB
**Created:** December 27, 2025
**Target Database:** `jal_sarovar_prod`
**Target Server:** www.jalsarovar.com
**Current Location:** `/var/www/jalsarovar`

---

## ✨ What's New in This Deployment

### Core Updates
- ✅ **Database renamed** from `jalsarovar_amrit_sarovar` to `jal_sarovar_prod`
- ✅ **Complete database backup** included (compressed SQL file)
- ✅ **Automatic deployment script** that preserves existing configuration
- ✅ **Automatic rollback capability** in case of issues
- ✅ **Smart detection** of user, group, and port from current deployment

### Deployment Features
- 🔍 **Pre-deployment analysis** - Detects current configuration
- 💾 **Automatic backups** - Backs up both application and database
- 🔄 **Zero-downtime preparation** - Stops service only when ready
- ✅ **Post-deployment verification** - Tests database and HTTP connectivity
- ↩️ **One-command rollback** - Instant recovery if needed

---

## 🚀 Quick Deployment (5 Steps)

### Step 1: Transfer Package to Server

```bash
# From your local machine
scp jalsarovar_deployment_complete_20251227_225552.tar.gz user@www.jalsarovar.com:/home/user/
```

### Step 2: SSH to Server

```bash
ssh user@www.jalsarovar.com
```

### Step 3: Extract Package

```bash
cd /home/user
tar -xzf jalsarovar_deployment_complete_20251227_225552.tar.gz
cd jalsarovar_deployment_complete_20251227_225552
```

### Step 4: Review Deployment Instructions

```bash
cat DEPLOY_INSTRUCTIONS.txt
```

### Step 5: Run Automatic Deployment

```bash
sudo ./auto_deploy_remote.sh jalsarovar_deployment_complete_20251227_225552.tar.gz
```

**That's it!** The script handles everything automatically.

---

## 🔍 What the Auto-Deploy Script Does

### Phase 1: Analysis
1. ✅ Detects current deployment directory (`/var/www/jalsarovar`)
2. ✅ Identifies user and group ownership (e.g., `www-data:www-data`)
3. ✅ Discovers current port (default: 5000)
4. ✅ Finds systemd service name (`jalsarovar` or `lab4all`)

### Phase 2: Backup
1. ✅ Creates timestamped backup of current application
2. ✅ Creates compressed backup of current database
3. ✅ Stores backups in `/var/backups/jalsarovar/`
4. ✅ Preserves old deployment as `.old` directory

### Phase 3: Deployment
1. ✅ Stops running application service
2. ✅ Extracts new deployment package
3. ✅ Replaces old deployment with new version
4. ✅ Sets correct ownership and permissions
5. ✅ Preserves existing `.env` configuration

### Phase 4: Database
1. ✅ Creates database if it doesn't exist
2. ✅ Offers to restore included database backup
3. ✅ Runs database migrations
4. ✅ Verifies database connectivity

### Phase 5: Service Configuration
1. ✅ Updates systemd service configuration
2. ✅ Configures correct paths and user
3. ✅ Updates nginx proxy settings (if needed)
4. ✅ Reloads systemd daemon

### Phase 6: Start & Verify
1. ✅ Starts application service
2. ✅ Tests HTTP connectivity
3. ✅ Verifies database connection
4. ✅ Displays deployment summary

---

## 📋 Detailed Deployment Workflow

### Before Deployment

The script will automatically:
- Preserve your existing `.env` file (passwords, secrets)
- Detect if you're using port 5000, 8000, or custom port
- Identify the correct user (usually `www-data` or `lab4all`)
- Backup everything before making changes

### During Deployment

**Terminal Output Example:**
```
========================================
Jal Sarovar - Automatic Deployment
========================================

✓ Deployment package found: jalsarovar_deployment_complete_20251227_225552.tar.gz

========================================
Step 1: Analyzing Current Deployment
========================================

✓ Found existing deployment at /var/www/jalsarovar
ℹ Current owner: www-data:www-data
ℹ Current port: 5000

========================================
Step 2: Backing Up Current Deployment
========================================

ℹ Creating backup of current application...
✓ Application backup created: /var/backups/jalsarovar/jalsarovar_backup_20251227_225552.tar.gz (25M)
ℹ Creating backup of current database...
✓ Database backup created: /var/backups/jalsarovar/jalsarovar_db_20251227_225552.sql.gz (4.2M)
✓ Backups stored in: /var/backups/jalsarovar

[... continues with all steps ...]

========================================
Deployment Complete!
========================================

Summary:
  Deployment Directory: /var/www/jalsarovar
  Application User:     www-data:www-data
  Application Port:     5000
  Database:             jal_sarovar_prod
  Systemd Service:      jalsarovar

Backup Locations:
  Application: /var/backups/jalsarovar/jalsarovar_backup_20251227_225552.tar.gz
  Database:    /var/backups/jalsarovar/jalsarovar_db_20251227_225552.sql.gz
  Old Version: /var/www/jalsarovar.old

Next Steps:
  1. Verify application: https://www.jalsarovar.com
  2. Check service status: systemctl status jalsarovar
  3. Monitor logs: journalctl -u jalsarovar -f
  4. If issues occur, rollback with: ./rollback_deployment.sh

✓ Deployment completed successfully!
```

---

## 🔄 Rollback Procedure

If deployment fails or issues arise:

### Quick Rollback (Single Command)

```bash
cd /home/user/jalsarovar_deployment_complete_20251227_225552
sudo ./rollback_deployment.sh
```

**The rollback script will:**
1. Stop the new version
2. Backup the failed deployment
3. Restore the previous version from `.old` directory
4. Restart the service
5. Reload nginx

**Rollback completes in ~30 seconds!**

### Manual Rollback (If Script Unavailable)

```bash
# Stop service
sudo systemctl stop jalsarovar

# Restore old version
sudo mv /var/www/jalsarovar /var/www/jalsarovar.failed
sudo mv /var/www/jalsarovar.old /var/www/jalsarovar

# Restart service
sudo systemctl start jalsarovar
sudo systemctl reload nginx
```

---

## 🔧 Configuration Management

### Environment Variables

The deployment script **preserves** your existing `.env` file and only updates:
- `DB_NAME` → `jal_sarovar_prod`
- `PORT` → (keeps existing port)

**Your passwords and secrets remain unchanged!**

### If Fresh Install (No Existing `.env`)

The script creates `.env` from `.env.production.template` and you'll need to configure:

```bash
# After deployment, edit .env
sudo nano /var/www/jalsarovar/.env
```

**Required Settings:**
```bash
# Generate a new secret key
SECRET_KEY=your-secure-random-key-here

# Database credentials
DB_PASSWORD=your-secure-db-password
DB_HOST=localhost
DB_USER=postgres

# Application
PORT=5000
FLASK_ENV=production
```

To generate a secure secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 🗄️ Database Restoration

### Automatic Restoration

During deployment, the script will ask:

```
Found database file: jalsarovar_database.sql.gz

WARNING: This will REPLACE all data in jal_sarovar_prod. Continue? [y/N]:
```

- Press **Y** to restore the included database
- Press **N** to skip and keep existing data

### Manual Database Restoration

If you skipped automatic restoration:

```bash
# Uncompress the database file
cd /var/www/jalsarovar/database
gunzip -c jalsarovar_database.sql.gz > jalsarovar_database.sql

# Restore to database
sudo -u postgres psql jal_sarovar_prod < jalsarovar_database.sql
```

---

## 📊 Post-Deployment Verification

### 1. Check Service Status

```bash
sudo systemctl status jalsarovar
```

**Expected Output:**
```
● jalsarovar.service - Jal Sarovar Water Quality Management
   Loaded: loaded (/etc/systemd/system/jalsarovar.service; enabled)
   Active: active (running) since ...
```

### 2. Test HTTP Connectivity

```bash
curl http://localhost:5000/
```

**Expected:** HTTP 200 or 302 response

### 3. Check Application Logs

```bash
# Real-time logs
sudo journalctl -u jalsarovar -f

# Last 50 lines
sudo journalctl -u jalsarovar -n 50
```

### 4. Verify Database Connection

```bash
cd /var/www/jalsarovar
sudo -u www-data /var/www/jalsarovar/venv/bin/python3 -c "
from app import create_app
app = create_app()
with app.app_context():
    from app import db
    from sqlalchemy import text
    result = db.session.execute(text('SELECT 1'))
    print('✓ Database connection successful')
"
```

### 5. Test Website

```bash
# From server
curl -I https://www.jalsarovar.com

# From local machine
open https://www.jalsarovar.com
```

---

## 📁 Deployment Directory Structure

After deployment:

```
/var/www/jalsarovar/
├── app/                          # Flask application
│   ├── controllers/              # Route handlers
│   ├── models/                   # Database models
│   ├── services/                 # Business logic
│   ├── static/                   # CSS, JS, images
│   └── templates/                # HTML templates
├── migrations/                   # Database migrations
├── database/                     # Database backup
│   └── jalsarovar_database.sql.gz
├── deployment/                   # Deployment scripts
├── venv/                         # Python virtual environment
├── config.py                     # Application config
├── app.py                        # Application entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (preserved)
├── auto_deploy_remote.sh         # Deployment script
└── rollback_deployment.sh        # Rollback script

/var/www/jalsarovar.old/          # Previous version (backup)
/var/backups/jalsarovar/          # Timestamped backups
```

---

## 🔐 Security Checklist

After deployment, verify:

- [ ] `.env` file has mode 600 (not world-readable)
- [ ] Database password is strong and secure
- [ ] `SECRET_KEY` is changed from default
- [ ] Application runs as non-root user (`www-data`)
- [ ] SSL/HTTPS is enabled on nginx
- [ ] Firewall allows only ports 80, 443, 22
- [ ] Database accepts connections only from localhost
- [ ] Fail2ban is configured for SSH protection

---

## 🛠️ Troubleshooting

### Issue: Service Won't Start

```bash
# Check detailed logs
sudo journalctl -u jalsarovar -xe

# Common causes:
# 1. Port already in use
sudo netstat -tlnp | grep :5000

# 2. Permission issues
sudo chown -R www-data:www-data /var/www/jalsarovar

# 3. Missing dependencies
cd /var/www/jalsarovar
sudo -u www-data venv/bin/pip install -r requirements.txt
```

### Issue: Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify database exists
sudo -u postgres psql -l | grep jal_sarovar

# Check credentials in .env
cat /var/www/jalsarovar/.env | grep DB_
```

### Issue: Nginx 502 Bad Gateway

```bash
# Check if application is running
sudo systemctl status jalsarovar

# Check nginx upstream port matches app port
sudo grep -A 5 "upstream jalsarovar" /etc/nginx/sites-available/jalsarovar

# Reload nginx
sudo systemctl reload nginx
```

### Issue: Permission Denied Errors

```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/jalsarovar

# Fix permissions
sudo chmod 755 /var/www/jalsarovar
sudo chmod 644 /var/www/jalsarovar/.env
sudo chmod +x /var/www/jalsarovar/venv/bin/*
```

---

## 📞 Support & Contact

**Deployment Issues:**
- Check logs: `journalctl -u jalsarovar -n 100`
- Review backup: `/var/backups/jalsarovar/`
- Use rollback: `./rollback_deployment.sh`

**Database Issues:**
- Backup location: `/var/backups/jalsarovar/jalsarovar_db_*.sql.gz`
- Restore: See "Database Restoration" section above

---

## 📝 Deployment Summary

**What Gets Updated:**
- ✅ Application code
- ✅ Python dependencies
- ✅ Database schema (via migrations)
- ✅ Configuration files (config.py)
- ✅ Systemd service definition

**What Gets Preserved:**
- ✅ `.env` environment variables
- ✅ User credentials and passwords
- ✅ Port configuration
- ✅ Nginx configuration
- ✅ SSL certificates
- ✅ Previous version (as backup)

**Deployment Time:** ~5-10 minutes (including database restoration)

---

## ✅ Final Checklist

After successful deployment:

- [ ] Application loads at https://www.jalsarovar.com
- [ ] Login works with existing credentials
- [ ] Database has expected data
- [ ] Service is enabled to start on boot
- [ ] Backups are stored in `/var/backups/jalsarovar/`
- [ ] Old version preserved in `/var/www/jalsarovar.old/`
- [ ] Logs show no errors
- [ ] SSL certificate is valid
- [ ] All critical functionality tested

---

**Deployment Package Created:** December 27, 2025
**Target Production Server:** www.jalsarovar.com
**Database:** jal_sarovar_prod
**Version:** Production Release v2.0
