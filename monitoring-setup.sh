#!/bin/bash
# ============================================================================
# Jal Sarovar Monitoring & Logging Setup
# ============================================================================
#
# This script sets up monitoring and logging infrastructure:
# - Log rotation for application logs
# - Health check monitoring
# - Database backup automation
# - Error alerting (optional Sentry integration)
#
# Usage:
#   sudo ./monitoring-setup.sh
#
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo "============================================================================"
echo "  Jal Sarovar - Monitoring & Logging Setup"
echo "============================================================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR]${NC} This script must be run as root or with sudo"
   exit 1
fi

# 1. Log Rotation Setup
log_info "Setting up log rotation..."

cat > /etc/logrotate.d/jalsarovar <<'EOF'
# Jal Sarovar Application Logs
/var/www/jalsarovar/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        supervisorctl restart jalsarovar > /dev/null 2>&1 || true
    endscript
}

# Nginx Logs for Jal Sarovar
/var/log/nginx/jalsarovar*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        nginx -s reload > /dev/null 2>&1 || true
    endscript
}
EOF

log_success "Log rotation configured (30 days retention)"

# 2. Health Check Monitoring Script
log_info "Creating health check monitoring script..."

mkdir -p /var/www/jalsarovar/scripts

cat > /var/www/jalsarovar/scripts/health_check.sh <<'EOF'
#!/bin/bash
# Health check script - monitors application availability

HEALTH_URL="http://localhost:8000/health"
LOG_FILE="/var/log/jalsarovar-health.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Perform health check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" --max-time 10)

if [ "$HTTP_CODE" -eq "200" ]; then
    echo "[$TIMESTAMP] ✓ HEALTHY (HTTP $HTTP_CODE)" >> "$LOG_FILE"
    exit 0
else
    echo "[$TIMESTAMP] ✗ UNHEALTHY (HTTP $HTTP_CODE)" >> "$LOG_FILE"

    # Optional: Send alert (uncomment and configure)
    # curl -X POST "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK" \
    #      -H 'Content-Type: application/json' \
    #      -d "{\"text\":\"🚨 Jal Sarovar Health Check Failed (HTTP $HTTP_CODE)\"}"

    exit 1
fi
EOF

chmod +x /var/www/jalsarovar/scripts/health_check.sh
log_success "Health check script created"

# 3. Database Backup Script
log_info "Creating database backup script..."

cat > /var/www/jalsarovar/scripts/db_backup.sh <<'EOF'
#!/bin/bash
# Database backup script - creates compressed PostgreSQL backups

BACKUP_DIR="/var/www/jalsarovar/backups"
DB_NAME="jal_sarovar_prod"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/jalsarovar_backup_$TIMESTAMP.sql"
LOG_FILE="/var/log/jalsarovar-backup.log"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Perform backup
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting database backup..." >> "$LOG_FILE"

sudo -u postgres pg_dump "$DB_NAME" > "$BACKUP_FILE" 2>&1

if [ $? -eq 0 ]; then
    # Compress backup
    gzip "$BACKUP_FILE"

    # Calculate size
    SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✓ Backup successful: $BACKUP_FILE.gz ($SIZE)" >> "$LOG_FILE"

    # Delete backups older than 30 days
    find "$BACKUP_DIR" -name "*.sql.gz" -type f -mtime +30 -delete

    exit 0
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✗ Backup failed!" >> "$LOG_FILE"
    exit 1
fi
EOF

chmod +x /var/www/jalsarovar/scripts/db_backup.sh
log_success "Database backup script created"

# 4. Setup Cron Jobs
log_info "Configuring cron jobs..."

# Create cron file
cat > /etc/cron.d/jalsarovar <<'EOF'
# Jal Sarovar Monitoring & Backup Jobs

# Health check every 5 minutes
*/5 * * * * root /var/www/jalsarovar/scripts/health_check.sh

# Database backup daily at 2 AM
0 2 * * * root /var/www/jalsarovar/scripts/db_backup.sh

# Log rotation test weekly
0 3 * * 0 root /usr/sbin/logrotate /etc/logrotate.d/jalsarovar
EOF

chmod 644 /etc/cron.d/jalsarovar
log_success "Cron jobs configured"

# 5. Create monitoring dashboard script
log_info "Creating monitoring dashboard script..."

cat > /var/www/jalsarovar/scripts/status_dashboard.sh <<'EOF'
#!/bin/bash
# Status Dashboard - Quick overview of system health

echo "============================================================================"
echo "  Jal Sarovar - System Status Dashboard"
echo "============================================================================"
echo ""

# Application Status
echo "APPLICATION:"
supervisorctl status jalsarovar | awk '{print "  " $0}'
echo ""

# Database Status
echo "DATABASE:"
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw jal_sarovar_prod; then
    CONN=$(sudo -u postgres psql -d jal_sarovar_prod -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='jal_sarovar_prod';")
    echo "  Status: Connected"
    echo "  Active Connections: $CONN"
else
    echo "  Status: Database not found"
fi
echo ""

# Redis Status
echo "REDIS:"
if systemctl is-active --quiet redis-server; then
    MEMORY=$(redis-cli INFO memory | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
    echo "  Status: Running"
    echo "  Memory Used: $MEMORY"
else
    echo "  Status: Not Running"
fi
echo ""

# Nginx Status
echo "NGINX:"
if systemctl is-active --quiet nginx; then
    echo "  Status: Running"
    nginx -v 2>&1 | awk '{print "  " $0}'
else
    echo "  Status: Not Running"
fi
echo ""

# Disk Space
echo "DISK SPACE:"
df -h / | tail -1 | awk '{print "  Root: " $3 " used / " $2 " total (" $5 " used)"}'
df -h /var | tail -1 | awk '{print "  /var: " $3 " used / " $2 " total (" $5 " used)"}'
echo ""

# Recent Health Checks
echo "RECENT HEALTH CHECKS:"
tail -5 /var/log/jalsarovar-health.log 2>/dev/null || echo "  No health check logs found"
echo ""

# Recent Backups
echo "RECENT BACKUPS:"
ls -lht /var/www/jalsarovar/backups/*.sql.gz 2>/dev/null | head -3 | awk '{print "  " $9 " (" $5 ", " $6 " " $7 ")"}' || echo "  No backups found"
echo ""

echo "============================================================================"
EOF

chmod +x /var/www/jalsarovar/scripts/status_dashboard.sh
log_success "Status dashboard created"

# 6. Test Health Check
log_info "Testing health check..."
/var/www/jalsarovar/scripts/health_check.sh
if [ $? -eq 0 ]; then
    log_success "Health check passed"
else
    echo -e "${YELLOW}[WARNING]${NC} Health check failed - application may not be running"
fi

# 7. Summary
echo ""
echo "============================================================================"
log_success "MONITORING SETUP COMPLETE!"
echo "============================================================================"
echo ""
log_info "Configured Components:"
echo "  ✓ Log rotation (30 days retention)"
echo "  ✓ Health check monitoring (every 5 minutes)"
echo "  ✓ Database backups (daily at 2 AM)"
echo "  ✓ Status dashboard"
echo ""
log_info "Useful Commands:"
echo "  View status dashboard:"
echo "    /var/www/jalsarovar/scripts/status_dashboard.sh"
echo ""
echo "  View health check log:"
echo "    tail -f /var/log/jalsarovar-health.log"
echo ""
echo "  View backup log:"
echo "    tail -f /var/log/jalsarovar-backup.log"
echo ""
echo "  Manual backup:"
echo "    /var/www/jalsarovar/scripts/db_backup.sh"
echo ""
log_info "Log Files:"
echo "  Application: /var/www/jalsarovar/logs/error.log"
echo "  Nginx Access: /var/log/nginx/jalsarovar-access.log"
echo "  Nginx Error: /var/log/nginx/jalsarovar-error.log"
echo "  Health Checks: /var/log/jalsarovar-health.log"
echo "  Backups: /var/log/jalsarovar-backup.log"
echo ""
