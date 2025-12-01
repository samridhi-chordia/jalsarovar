# Jal Sarovar - Production Deployment Package

**Version:** 1.0.0
**Release Date:** December 1, 2025
**Package Type:** Production Deployment

---

## Overview

This package contains everything needed to deploy **Jal Sarovar** (Water Quality Monitoring and Management System) on a production cloud server. The application is a comprehensive Flask-based web platform for monitoring and managing water quality across multiple sites with advanced ML analytics.

## What's Included

### Application Components
- **Complete Source Code** - Full Flask application with all features
- **Production Database** - 378,000+ test results, 68,000+ monitoring sites (27MB compressed)
- **Deployment Automation** - One-command deployment script
- **Comprehensive Documentation** - Setup, deployment, and troubleshooting guides

### Key Features
- Voice Agent (IVR Notifications)
- Risk Prediction (Site Risk Assessment)
- WQI Calculator (Water Quality Index)
- ML Analytics (Anomaly Detection, Forecasting, Site Risk Classification)
- Data Import/Export (CSV wizards)
- Intervention Tracking
- Residential Monitoring (Raspberry Pi integration)
- Admin Dashboard

---

## Package Contents

```
jalsarovar_RELEASE/
├── app/                              # Application source code (4.8MB)
│   ├── controllers/                  # Route controllers
│   ├── models/                       # Database models
│   ├── services/                     # Business logic
│   ├── templates/                    # HTML templates
│   ├── static/                       # CSS, JS, images
│   └── ml/                          # ML models and algorithms
├── database/
│   └── jalsarovar_production.sql.gz  # Compressed database (27MB)
├── docs/
│   ├── README.md                     # Full functional specifications
│   ├── QUICKSTART.md                 # Quick start guide
│   └── DEPLOYMENT_GUIDE.md           # Detailed deployment instructions
├── app.py                            # Flask application entry point
├── config.py                         # Configuration classes
├── requirements.txt                  # Python dependencies
└── deploy.sh                         # Automated deployment script
```

---

## Quick Deployment

### Prerequisites
- Fresh Ubuntu 20.04+ or Debian 11+ server (64-bit)
- Root/sudo access
- 4GB RAM minimum (8GB recommended)
- 20GB free disk space minimum
- Python 3.8 or higher

### Deployment Steps

**1. Upload package to your server:**
```bash
# On your local machine
scp -r jalsarovar_RELEASE root@your-server-ip:/tmp/

# SSH into your server
ssh root@your-server-ip
```

**2. Run the automated deployment script:**
```bash
cd /tmp/jalsarovar_RELEASE
sudo bash deploy.sh
```

The script automatically:
- Installs system dependencies (Python, Nginx, PostgreSQL, Supervisor, etc.)
- Creates application directory structure at `/var/www/jalsarovar`
- Deploys application files
- Sets up Python virtual environment
- Imports production database
- Configures Nginx as reverse proxy
- Sets up Supervisor for process management
- Configures automatic daily backups
- Runs health checks

**3. Access your application:**
```
http://your-server-ip/
```

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

**IMPORTANT:** Change the admin password immediately after first login!

---

## Manual Deployment

If you prefer to deploy manually or customize the process, see the detailed step-by-step guide in:
- `docs/DEPLOYMENT_GUIDE.md`

The manual deployment process covers:
- System dependency installation
- Application directory setup
- Virtual environment configuration
- Database import
- Nginx configuration
- Supervisor setup
- SSL/TLS configuration
- Security hardening

---

## System Requirements

### Minimum Requirements
- **OS:** Ubuntu 20.04 LTS or Debian 11+ (64-bit)
- **RAM:** 4 GB (8 GB recommended)
- **Storage:** 20 GB free space (50 GB recommended)
- **CPU:** 2 cores (4 cores recommended)
- **Python:** 3.8 or higher

### Recommended Cloud Platforms
- AWS EC2 (t3.medium or larger)
- DigitalOcean Droplet (4GB RAM or larger)
- Google Cloud Compute Engine (e2-medium or larger)
- Azure Virtual Machine (B2s or larger)

### Network Requirements
- Open ports: 80 (HTTP), 443 (HTTPS)
- Stable internet connection
- Domain name (optional but recommended for SSL)

---

## Post-Deployment Configuration

### 1. Setup SSL Certificate (Highly Recommended)
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

### 3. Change Admin Password
1. Login at `http://your-domain.com/`
2. Navigate to User Settings
3. Change password to a strong password

### 4. Setup Email Notifications (Optional)
Edit `/var/www/jalsarovar/.env`:
```bash
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

---

## Application Management

### Check Application Status
```bash
sudo supervisorctl status jalsarovar
```

### Restart Application
```bash
sudo supervisorctl restart jalsarovar
```

### View Logs
```bash
# Application error logs
tail -f /var/www/jalsarovar/logs/error.log

# Application access logs
tail -f /var/www/jalsarovar/logs/access.log

# Nginx logs
tail -f /var/log/nginx/error.log
```

### Manual Database Backup
```bash
sudo -u www-data /var/www/jalsarovar/backup.sh
```

### Restart All Services
```bash
sudo supervisorctl restart jalsarovar
sudo systemctl restart nginx
```

---

## Database Information

### Production Database Details
- **Format:** SQLite 3
- **Compressed Size:** 27 MB (gzipped SQL dump)
- **Uncompressed Size:** ~220 MB
- **Total Test Results:** 378,000+
- **Total Monitoring Sites:** 68,000+
- **Data Sources:** US (USGS), India (CPCB), synthetic data

### Database Location (After Deployment)
- **Path:** `/var/www/jalsarovar/instance/jalsarovar.db`
- **Backups:** `/var/www/jalsarovar/backups/`
- **Backup Schedule:** Daily at 2:00 AM (automated via cron)

---

## Security Considerations

### Implemented Security Features
- Secure password hashing (bcrypt)
- SQL injection prevention (SQLAlchemy ORM)
- CSRF protection (Flask-WTF)
- Secure session management
- File upload validation
- User authentication and authorization

### Recommended Security Hardening
1. **Enable SSL/TLS** - Use Let's Encrypt for free certificates
2. **Configure Firewall** - Use UFW to restrict access
3. **Disable SSH Password Authentication** - Use SSH keys only
4. **Install Fail2Ban** - Prevent brute force attacks
5. **Regular Updates** - Keep system and dependencies updated
6. **Change Default Credentials** - Immediately after deployment
7. **Restrict Database Access** - Set proper file permissions
8. **Enable Security Headers** - Configure in Nginx

See `docs/DEPLOYMENT_GUIDE.md` for detailed security hardening steps.

---

## Troubleshooting

### Application Won't Start
```bash
# Check supervisor status
sudo supervisorctl status jalsarovar

# Check error logs
tail -100 /var/www/jalsarovar/logs/error.log

# Restart application
sudo supervisorctl restart jalsarovar
```

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

# Restart application
sudo supervisorctl restart jalsarovar
```

### High Memory Usage
```bash
# Check memory usage
free -h

# Reduce Gunicorn workers (edit supervisor config)
sudo nano /etc/supervisor/conf.d/jalsarovar.conf
# Change --workers to 2
sudo supervisorctl restart jalsarovar
```

For more troubleshooting help, see `docs/DEPLOYMENT_GUIDE.md`.

---

## Backup and Recovery

### Automated Backups
Backups run automatically daily at 2:00 AM via cron job.

**Check backup schedule:**
```bash
crontab -u www-data -l
```

**Verify backups:**
```bash
ls -lh /var/www/jalsarovar/backups/
```

### Manual Backup
```bash
# Backup database
sudo -u www-data /var/www/jalsarovar/backup.sh

# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz /var/www/jalsarovar/uploads/
```

### Restore from Backup
```bash
# Stop application
sudo supervisorctl stop jalsarovar

# Restore database
gunzip -c backup_20250101.sql.gz | \
    sqlite3 /var/www/jalsarovar/instance/jalsarovar.db

# Start application
sudo supervisorctl start jalsarovar
```

---

## Monitoring and Maintenance

### Daily Tasks
- Check application logs for errors
- Monitor disk space usage
- Verify backups are running

### Weekly Tasks
- Review application performance
- Check for security updates
- Review user activity logs

### Monthly Tasks
- Update system packages
- Review and rotate logs
- Test backup restoration
- Review security configuration

### Performance Monitoring
```bash
# Check disk usage
df -h
du -sh /var/www/jalsarovar/*

# Check database size
ls -lh /var/www/jalsarovar/instance/jalsarovar.db

# Monitor system resources
htop
```

---

## Documentation

### Included Documentation
- `docs/README.md` - Full functional specifications and feature descriptions
- `docs/QUICKSTART.md` - Quick start guide for development
- `docs/DEPLOYMENT_GUIDE.md` - Comprehensive deployment instructions

### Additional Resources
- Application logs: `/var/www/jalsarovar/logs/`
- Nginx configuration: `/etc/nginx/sites-available/jalsarovar`
- Supervisor configuration: `/etc/supervisor/conf.d/jalsarovar.conf`
- Environment configuration: `/var/www/jalsarovar/.env`

---

## Technology Stack

### Backend
- **Framework:** Flask 3.0.0
- **Database:** SQLite 3 (PostgreSQL supported)
- **ORM:** SQLAlchemy 2.0.23
- **WSGI Server:** Gunicorn 21.2.0

### Frontend
- **Template Engine:** Jinja2
- **CSS Framework:** Bootstrap 5
- **JavaScript:** Vanilla JS + Chart.js

### ML/Analytics
- **Libraries:** scikit-learn, pandas, numpy
- **Models:** Random Forest, XGBoost, Bayesian Optimization

### Deployment
- **Web Server:** Nginx
- **Process Manager:** Supervisor
- **OS:** Ubuntu/Debian Linux

### Notifications
- **Voice/SMS:** Twilio API integration

---

## Support and Contact

For issues, questions, or feature requests:

1. Review the troubleshooting section in `docs/DEPLOYMENT_GUIDE.md`
2. Check application logs for error details
3. Verify all dependencies are installed correctly
4. Ensure system meets minimum requirements

---

## Version Information

**Application Version:** 1.0.0
**Release Type:** Production
**Release Date:** December 1, 2025
**Python Version Required:** 3.8+
**Flask Version:** 3.0.0

---

## License

Jal Sarovar - Water Quality Monitoring and Management System
Copyright (c) 2025

---

## Quick Reference

### Important File Locations (After Deployment)
- Application: `/var/www/jalsarovar/`
- Database: `/var/www/jalsarovar/instance/jalsarovar.db`
- Logs: `/var/www/jalsarovar/logs/`
- Backups: `/var/www/jalsarovar/backups/`
- Uploads: `/var/www/jalsarovar/uploads/`

### Important Commands
```bash
# Start application
sudo supervisorctl start jalsarovar

# Stop application
sudo supervisorctl stop jalsarovar

# Restart application
sudo supervisorctl restart jalsarovar

# Check status
sudo supervisorctl status jalsarovar

# View logs
tail -f /var/www/jalsarovar/logs/error.log

# Backup database
sudo -u www-data /var/www/jalsarovar/backup.sh

# Restart Nginx
sudo systemctl restart nginx
```

### Default Credentials
- **Username:** admin
- **Password:** admin123
- **Change immediately after first login!**

---

**Ready to deploy?** Run `sudo bash deploy.sh` and your application will be live in minutes!
