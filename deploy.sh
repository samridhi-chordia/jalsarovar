#!/bin/bash
# ============================================================================
# Jal Sarovar Deployment Script
# ============================================================================
#
# This script handles deployment of the Jal Sarovar application
# Supports: staging and production environments
#
# Usage:
#   ./deploy.sh [environment]
#   ./deploy.sh staging
#   ./deploy.sh production
#
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/var/www/jalsarovar"
VENV_DIR="$APP_DIR/venv"
BACKUP_DIR="$APP_DIR/backups"
ENVIRONMENT="${1:-production}"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo ""
echo "============================================================================"
echo "  Jal Sarovar - Water Quality Management System"
echo "  Deployment Script"
echo "============================================================================"
echo ""
log_info "Environment: $ENVIRONMENT"
echo ""

# Pre-deployment checks
log_info "Running pre-deployment checks..."

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root or with sudo"
   exit 1
fi

# Check if .env file exists
if [ ! -f "$APP_DIR/.env" ]; then
    log_error ".env file not found!"
    log_info "Copy .env.production.example to .env and configure it:"
    log_info "  cp .env.production.example .env"
    exit 1
fi

# Check if Redis is running
if ! systemctl is-active --quiet redis-server; then
    log_warning "Redis server is not running. Starting..."
    systemctl start redis-server
    log_success "Redis server started"
fi

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    log_error "PostgreSQL server is not running!"
    exit 1
fi

log_success "Pre-deployment checks passed"
echo ""

# Backup database
log_info "Creating database backup..."
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/jalsarovar_backup_$TIMESTAMP.sql"

sudo -u postgres pg_dump jal_sarovar_prod > "$BACKUP_FILE" 2>/dev/null || true
if [ -f "$BACKUP_FILE" ]; then
    gzip "$BACKUP_FILE"
    log_success "Database backup created: $BACKUP_FILE.gz"
else
    log_warning "Database backup skipped (database may not exist yet)"
fi
echo ""

# Pull latest code (if using git)
if [ -d "$APP_DIR/.git" ]; then
    log_info "Pulling latest code from repository..."
    cd "$APP_DIR"
    git pull origin main || log_warning "Git pull failed or not configured"
    log_success "Code updated"
    echo ""
fi

# Install/Update dependencies
log_info "Installing Python dependencies..."
cd "$APP_DIR"
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt --quiet
log_success "Dependencies installed"
echo ""

# Run database migrations
log_info "Running database migrations..."
export FLASK_APP=app.py
flask db upgrade
log_success "Database migrations completed"
echo ""

# Collect static files (if applicable)
log_info "Preparing static files..."
mkdir -p "$APP_DIR/uploads"
chmod 755 "$APP_DIR/uploads"
log_success "Static files prepared"
echo ""

# Test configuration
log_info "Testing application configuration..."
python -c "
from app import create_app
app = create_app('$ENVIRONMENT')
with app.app_context():
    from app import db
    # Test database connection
    db.engine.connect()
    print('✓ Database connection: OK')

    # Test Redis connection
    import redis
    r = redis.Redis(host='localhost', port=6379)
    r.ping()
    print('✓ Redis connection: OK')

    # Check critical config
    assert app.config.get('SECRET_KEY'), 'SECRET_KEY not set'
    print('✓ SECRET_KEY: OK')

    if '$ENVIRONMENT' == 'production':
        assert app.config.get('SESSION_COOKIE_SECURE') == True, 'SESSION_COOKIE_SECURE must be True'
        print('✓ SESSION_COOKIE_SECURE: OK')

    print('✓ Configuration: OK')
"
log_success "Configuration tests passed"
echo ""

# Restart application
log_info "Restarting application..."
supervisorctl restart jalsarovar
sleep 3

# Check if application is running
if supervisorctl status jalsarovar | grep -q "RUNNING"; then
    log_success "Application restarted successfully"
else
    log_error "Application failed to start!"
    log_info "Check logs: sudo tail -50 /var/log/supervisor/jalsarovar-stderr.log"
    exit 1
fi
echo ""

# Health check
log_info "Running health check..."
sleep 2

# Check if application responds
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ || echo "000")
if [ "$HTTP_CODE" -eq "200" ] || [ "$HTTP_CODE" -eq "302" ]; then
    log_success "Application is responding (HTTP $HTTP_CODE)"
else
    log_warning "Application may not be responding correctly (HTTP $HTTP_CODE)"
fi
echo ""

# Reload Nginx (if configured)
if systemctl is-active --quiet nginx; then
    log_info "Reloading Nginx..."
    nginx -t && systemctl reload nginx
    log_success "Nginx reloaded"
else
    log_warning "Nginx not running or not configured"
fi
echo ""

# Final status
echo "============================================================================"
log_success "DEPLOYMENT COMPLETE!"
echo "============================================================================"
echo ""
log_info "Application Status:"
supervisorctl status jalsarovar
echo ""
log_info "Next Steps:"
echo "  1. Test the application: http://your-domain.com"
echo "  2. Monitor logs: sudo tail -f /var/log/supervisor/jalsarovar-*.log"
echo "  3. Check error logs if issues occur"
echo ""
log_info "Backup Location: $BACKUP_DIR"
echo ""

# Show recent logs
log_info "Recent application logs:"
tail -20 /var/log/supervisor/jalsarovar-stdout.log 2>/dev/null || echo "No logs available"
echo ""
