# Deploy Lab4All to www.jalsarovar.com - Quick Start

**Target Server**: www.jalsarovar.com (existing cloud server)
**Method**: SCP + Tar + Automated Setup
**Time Required**: 15-30 minutes

---

## Prerequisites Check

Before starting, ensure you have:

- [ ] SSH access to www.jalsarovar.com
- [ ] Database credentials (PostgreSQL)
- [ ] Sudo/root access on remote server
- [ ] Server has PostgreSQL 15 installed

---

## 🚀 Quick Deployment (3 Steps)

### Step 1: Create and Transfer Package (On Your Mac)

```bash
# Navigate to application directory
cd /Users/test/lab4all_wflow_RELEASE_RONALD/lab4all_webapp

# Create deployment package
./deployment/scripts/create_deployment_package.sh

# Transfer to server (replace 'user' with your SSH username)
scp lab4all_webapp_*.tar.gz user@www.jalsarovar.com:/tmp/
```

**Expected Output**:
```
Package created successfully!
Package location: /Users/test/.../lab4all_webapp_20250122_143022.tar.gz
Package size: 45M

Next steps:
1. Transfer to remote server:
   scp lab4all_webapp_20250122_143022.tar.gz user@www.jalsarovar.com:/tmp/
```

### Step 2: Connect and Extract (On Remote Server)

```bash
# SSH to server
ssh user@www.jalsarovar.com

# Navigate to /tmp
cd /tmp

# Extract package
tar -xzf lab4all_webapp_*.tar.gz

# Enter extracted directory
cd lab4all_webapp_*
```

### Step 3: Run Automated Setup (On Remote Server)

```bash
# Run setup script (requires sudo)
sudo bash deployment/scripts/remote_setup.sh
```

**You will be prompted for**:

| Prompt | Example Value | Notes |
|--------|---------------|-------|
| Domain name | `www.jalsarovar.com` | Your domain |
| Database host | `localhost` | Or remote DB IP |
| Database port | `5432` | Default PostgreSQL port |
| Database name | `jal_sarovar_prod` | Production database |
| Database user | `postgres` | Or dedicated user |
| Database password | `********` | Your DB password |
| Flask secret key | *[press Enter]* | Auto-generates if blank |
| Enable SSL | `y` | Recommended |

**Setup Process** (automatic):
1. ✓ Installs system dependencies (Python 3.11, Nginx, etc.)
2. ✓ Creates application user (`lab4all`)
3. ✓ Copies files to `/opt/lab4all/`
4. ✓ Sets up Python virtual environment
5. ✓ Installs Python packages
6. ✓ Configures environment variables
7. ✓ Tests database connection
8. ✓ Runs database migrations
9. ✓ Configures systemd service
10. ✓ Configures Nginx reverse proxy
11. ✓ Configures firewall
12. ✓ Starts application

**Duration**: 10-15 minutes

---

## ✅ Verify Deployment

After setup completes:

### 1. Check Service Status

```bash
sudo systemctl status lab4all
```

**Expected**: `Active: active (running)`

### 2. Test Application

```bash
# Test local endpoint
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "service": "jal-sarovar"}
```

### 3. Test via Browser

Open: **http://www.jalsarovar.com**

You should see the Lab4All homepage.

---

## 🔒 Enable HTTPS (Recommended)

After HTTP deployment works:

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain SSL certificate (follow prompts)
sudo certbot --nginx -d www.jalsarovar.com

# Test renewal
sudo certbot renew --dry-run
```

**Done!** Your site is now accessible at: **https://www.jalsarovar.com**

---

## 📝 Post-Deployment Tasks

### 1. Create Admin User

```bash
cd /opt/lab4all/lab4all_webapp
sudo -u lab4all /opt/lab4all/venv/bin/python3 -c "
from app import create_app, db
from app.models import User
app = create_app('production')
with app.app_context():
    admin = User(username='admin', email='admin@jalsarovar.com', is_admin=True)
    admin.set_password('YourSecurePassword123!')
    db.session.add(admin)
    db.session.commit()
    print('✓ Admin user created')
"
```

### 2. Upload ML Models (Optional)

If you have pre-trained models on your Mac:

```bash
# From your Mac
scp -r /path/to/ALL_MODELS/* user@www.jalsarovar.com:/tmp/models/

# On remote server
sudo mkdir -p /opt/lab4all/lab4all_webapp/models
sudo mv /tmp/models/* /opt/lab4all/lab4all_webapp/models/
sudo chown -R lab4all:lab4all /opt/lab4all/lab4all_webapp/models
```

### 3. Set Up Automated Backups

```bash
# Add backup to crontab (runs daily at 2 AM)
sudo crontab -e

# Add this line:
0 2 * * * /opt/lab4all/lab4all_webapp/deployment/scripts/backup.sh
```

---

## 🔧 Common Management Commands

### View Logs

```bash
# Application logs (live)
sudo journalctl -u lab4all -f

# Recent errors
sudo journalctl -u lab4all -n 100 --no-pager

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Restart Application

```bash
sudo systemctl restart lab4all
```

### Stop Application

```bash
sudo systemctl stop lab4all
```

### Check Status

```bash
sudo systemctl status lab4all
sudo systemctl status nginx
```

---

## 🐛 Troubleshooting

### Application Won't Start

```bash
# Check logs for errors
sudo journalctl -u lab4all -n 50

# Common issues:
# 1. Database connection - verify .env.production
# 2. Port in use - check: sudo lsof -i :8000
# 3. Permissions - check: ls -la /opt/lab4all/
```

### Can't Access Website

```bash
# Test application directly
curl http://localhost:8000/health

# If works, check Nginx
sudo nginx -t
sudo systemctl status nginx

# If fails, check firewall
sudo ufw status
```

### Database Connection Error

```bash
# Test database connection
PGPASSWORD=your-password psql -h localhost -U postgres -d jal_sarovar_prod -c "SELECT 1"

# Check PostgreSQL is running
sudo systemctl status postgresql
```

---

## 🔄 Update Deployed Application

When you need to deploy code changes:

```bash
# 1. On your Mac - create new package
cd /Users/test/lab4all_wflow_RELEASE_RONALD/lab4all_webapp
./deployment/scripts/create_deployment_package.sh
scp lab4all_webapp_*.tar.gz user@www.jalsarovar.com:/tmp/

# 2. On server - backup and update
ssh user@www.jalsarovar.com
sudo systemctl stop lab4all
sudo mv /opt/lab4all/lab4all_webapp /opt/lab4all/lab4all_webapp.backup.$(date +%Y%m%d)
cd /tmp
tar -xzf lab4all_webapp_*.tar.gz
sudo cp -r lab4all_webapp_*/* /opt/lab4all/lab4all_webapp/
sudo chown -R lab4all:lab4all /opt/lab4all
cd /opt/lab4all/lab4all_webapp
sudo -u lab4all /opt/lab4all/venv/bin/flask db upgrade
sudo systemctl start lab4all
```

---

## 📊 System Requirements

**Minimum**:
- 2 CPU cores
- 4 GB RAM
- 20 GB disk space
- Ubuntu 20.04 or 22.04

**Recommended for Production**:
- 4 CPU cores
- 8 GB RAM
- 100 GB disk space (with auto-scaling)

---

## 📂 File Locations

After deployment:

```
/opt/lab4all/
├── venv/                              # Python virtual environment
└── lab4all_webapp/                    # Application code
    ├── app/                           # Flask application
    ├── uploads/                       # User uploads
    ├── models/                        # ML models
    ├── .env.production               # Configuration (sensitive!)

/var/log/lab4all/                      # Application logs
/etc/systemd/system/lab4all.service   # Service configuration
/etc/nginx/sites-available/lab4all    # Nginx configuration
```

---

## 🆘 Need Help?

### View Complete Documentation

```bash
# On remote server
cat /opt/lab4all/lab4all_webapp/deployment/REMOTE_DEPLOYMENT.md
```

Or on your Mac:
```bash
cat /Users/test/lab4all_wflow_RELEASE_RONALD/lab4all_webapp/deployment/REMOTE_DEPLOYMENT.md
```

### Quick Health Check

```bash
# Run this on remote server
echo "=== System Status ===" && \
systemctl is-active lab4all && \
systemctl is-active nginx && \
systemctl is-active postgresql && \
curl -s http://localhost:8000/health && \
echo -e "\n✓ All services running"
```

### Support Resources

1. **Application logs**: `sudo journalctl -u lab4all -f`
2. **Nginx logs**: `sudo tail -f /var/log/nginx/error.log`
3. **System logs**: `sudo tail -f /var/log/syslog`
4. **Database logs**: `sudo tail -f /var/log/postgresql/*.log`

---

## ✨ Success Checklist

After deployment:

- [x] Application accessible at http://www.jalsarovar.com
- [ ] SSL certificate installed (https://www.jalsarovar.com)
- [ ] Admin user created
- [ ] Database backups scheduled
- [ ] Monitoring configured
- [ ] ML models uploaded (if applicable)

---

## 🎯 Quick Command Reference

```bash
# Application
sudo systemctl restart lab4all           # Restart app
sudo journalctl -u lab4all -f           # View logs

# Nginx
sudo systemctl reload nginx              # Reload config
sudo nginx -t                            # Test config

# Database
sudo -u postgres psql jal_sarovar_prod  # Connect to DB

# System
sudo ufw status                          # Check firewall
df -h                                    # Check disk space
free -h                                  # Check memory
htop                                     # System monitor
```

---

**🎉 Deployment Complete!**

Your Lab4All Water Quality Management System is now running at:
- **HTTP**: http://www.jalsarovar.com
- **HTTPS**: https://www.jalsarovar.com (after SSL setup)

---

**Last Updated**: December 22, 2025
**Version**: 1.0
**For**: www.jalsarovar.com deployment
