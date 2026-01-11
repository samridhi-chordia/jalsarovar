#!/bin/bash

##############################################################################
# Jal Sarovar - Automatic Remote Deployment Script
# Safely deploys new version while preserving existing configuration
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
DEPLOYMENT_DIR="/var/www/jalsarovar"
BACKUP_DIR="/var/backups/jalsarovar"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="jal_sarovar_prod"

##############################################################################
# Helper Functions
##############################################################################

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root or with sudo"
        exit 1
    fi
}

##############################################################################
# Pre-Deployment Checks
##############################################################################

print_header "Jal Sarovar - Automatic Deployment"

check_root

# Check if deployment package is provided
if [ -z "$1" ]; then
    print_error "Usage: sudo ./auto_deploy_remote.sh <deployment_package.tar.gz>"
    echo ""
    echo "Example:"
    echo "  sudo ./auto_deploy_remote.sh jalsarovar_deployment_20251227_223949.tar.gz"
    echo ""
    exit 1
fi

DEPLOYMENT_PACKAGE="$1"

if [ ! -f "$DEPLOYMENT_PACKAGE" ]; then
    print_error "Deployment package not found: $DEPLOYMENT_PACKAGE"
    exit 1
fi

print_success "Deployment package found: $DEPLOYMENT_PACKAGE"

##############################################################################
# Step 1: Gather Current Configuration
##############################################################################

print_header "Step 1: Analyzing Current Deployment"

if [ ! -d "$DEPLOYMENT_DIR" ]; then
    print_warning "No existing deployment found at $DEPLOYMENT_DIR"
    print_info "Will create fresh installation"
    CURRENT_USER="www-data"
    CURRENT_GROUP="www-data"
    CURRENT_PORT="5000"
    FRESH_INSTALL=true
else
    print_success "Found existing deployment at $DEPLOYMENT_DIR"

    # Get current ownership
    CURRENT_USER=$(stat -c '%U' "$DEPLOYMENT_DIR" 2>/dev/null || stat -f '%Su' "$DEPLOYMENT_DIR")
    CURRENT_GROUP=$(stat -c '%G' "$DEPLOYMENT_DIR" 2>/dev/null || stat -f '%Sg' "$DEPLOYMENT_DIR")

    print_info "Current owner: ${CURRENT_USER}:${CURRENT_GROUP}"

    # Try to detect current port
    if [ -f "$DEPLOYMENT_DIR/.env" ]; then
        CURRENT_PORT=$(grep "^PORT=" "$DEPLOYMENT_DIR/.env" | cut -d'=' -f2 || echo "5000")
    else
        CURRENT_PORT="5000"
    fi

    # Check systemd service for port
    if [ -f "/etc/systemd/system/jalsarovar.service" ]; then
        SERVICE_PORT=$(grep -oP 'PORT=\K\d+' /etc/systemd/system/jalsarovar.service || echo "")
        if [ ! -z "$SERVICE_PORT" ]; then
            CURRENT_PORT="$SERVICE_PORT"
        fi
    fi

    print_info "Current port: ${CURRENT_PORT}"

    FRESH_INSTALL=false
fi

##############################################################################
# Step 2: Create Backup of Current Deployment
##############################################################################

if [ "$FRESH_INSTALL" = false ]; then
    print_header "Step 2: Backing Up Current Deployment"

    mkdir -p "$BACKUP_DIR"

    print_info "Creating backup of current application..."
    BACKUP_FILE="${BACKUP_DIR}/jalsarovar_backup_${TIMESTAMP}.tar.gz"

    cd /var/www
    tar -czf "$BACKUP_FILE" jalsarovar/ 2>/dev/null || true

    if [ -f "$BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        print_success "Application backup created: $BACKUP_FILE ($BACKUP_SIZE)"
    else
        print_warning "Could not create application backup"
    fi

    # Backup current database
    print_info "Creating backup of current database..."
    DB_BACKUP_FILE="${BACKUP_DIR}/jalsarovar_db_${TIMESTAMP}.sql"

    sudo -u postgres pg_dump "$DB_NAME" > "$DB_BACKUP_FILE" 2>/dev/null || {
        print_warning "Could not backup database (may not exist yet)"
        DB_BACKUP_FILE=""
    }

    if [ ! -z "$DB_BACKUP_FILE" ] && [ -f "$DB_BACKUP_FILE" ]; then
        gzip "$DB_BACKUP_FILE"
        DB_BACKUP_SIZE=$(du -h "${DB_BACKUP_FILE}.gz" | cut -f1)
        print_success "Database backup created: ${DB_BACKUP_FILE}.gz ($DB_BACKUP_SIZE)"
    fi

    print_success "Backups stored in: $BACKUP_DIR"
else
    print_header "Step 2: Skipping Backup (Fresh Install)"
fi

##############################################################################
# Step 3: Stop Running Application
##############################################################################

if [ "$FRESH_INSTALL" = false ]; then
    print_header "Step 3: Stopping Current Application"

    # Try systemd service
    if systemctl is-active --quiet jalsarovar; then
        print_info "Stopping jalsarovar systemd service..."
        systemctl stop jalsarovar
        print_success "Service stopped"
    elif systemctl is-active --quiet lab4all; then
        print_info "Stopping lab4all systemd service..."
        systemctl stop lab4all
        print_success "Service stopped"
    else
        print_info "No systemd service found running"
    fi

    # Kill any remaining gunicorn processes
    if pgrep -f "gunicorn.*jalsarovar" > /dev/null; then
        print_info "Stopping gunicorn processes..."
        pkill -f "gunicorn.*jalsarovar" || true
        sleep 2
        print_success "Gunicorn processes stopped"
    fi
else
    print_header "Step 3: Skipping Service Stop (Fresh Install)"
fi

##############################################################################
# Step 4: Extract New Deployment
##############################################################################

print_header "Step 4: Extracting New Deployment"

# Create temp directory
TEMP_EXTRACT="/tmp/jalsarovar_deploy_${TIMESTAMP}"
mkdir -p "$TEMP_EXTRACT"

print_info "Extracting deployment package..."
tar -xzf "$DEPLOYMENT_PACKAGE" -C "$TEMP_EXTRACT"

# Find the extracted directory
EXTRACTED_DIR=$(find "$TEMP_EXTRACT" -maxdepth 1 -type d -name "jalsarovar_deployment_*" | head -1)

if [ -z "$EXTRACTED_DIR" ]; then
    print_error "Could not find extracted deployment directory"
    exit 1
fi

print_success "Extracted to: $EXTRACTED_DIR"

##############################################################################
# Step 5: Deploy New Version
##############################################################################

print_header "Step 5: Deploying New Version"

# Backup and remove old deployment
if [ "$FRESH_INSTALL" = false ]; then
    print_info "Removing old deployment..."
    rm -rf "${DEPLOYMENT_DIR}.old" 2>/dev/null || true
    mv "$DEPLOYMENT_DIR" "${DEPLOYMENT_DIR}.old"
fi

# Move new deployment
print_info "Installing new version..."
mv "$EXTRACTED_DIR" "$DEPLOYMENT_DIR"

# Set ownership
print_info "Setting ownership to ${CURRENT_USER}:${CURRENT_GROUP}..."
chown -R "${CURRENT_USER}:${CURRENT_GROUP}" "$DEPLOYMENT_DIR"

# Set permissions
chmod 755 "$DEPLOYMENT_DIR"
chmod -R 755 "$DEPLOYMENT_DIR/app"
chmod 644 "$DEPLOYMENT_DIR"/.env.production.template

print_success "New version deployed"

##############################################################################
# Step 6: Configure Environment
##############################################################################

print_header "Step 6: Configuring Environment"

cd "$DEPLOYMENT_DIR"

# Check if old .env exists
if [ -f "${DEPLOYMENT_DIR}.old/.env" ]; then
    print_info "Preserving existing .env configuration..."
    cp "${DEPLOYMENT_DIR}.old/.env" "$DEPLOYMENT_DIR/.env"

    # Update DB_NAME if needed
    if grep -q "^DB_NAME=" "$DEPLOYMENT_DIR/.env"; then
        sed -i "s/^DB_NAME=.*/DB_NAME=${DB_NAME}/" "$DEPLOYMENT_DIR/.env"
    else
        echo "DB_NAME=${DB_NAME}" >> "$DEPLOYMENT_DIR/.env"
    fi

    # Update PORT if needed
    if grep -q "^PORT=" "$DEPLOYMENT_DIR/.env"; then
        sed -i "s/^PORT=.*/PORT=${CURRENT_PORT}/" "$DEPLOYMENT_DIR/.env"
    else
        echo "PORT=${CURRENT_PORT}" >> "$DEPLOYMENT_DIR/.env"
    fi

    print_success "Configuration preserved and updated"
else
    print_warning "No existing .env found"

    # Create from template
    if [ -f "$DEPLOYMENT_DIR/.env.production.template" ]; then
        print_info "Creating .env from template..."
        cp "$DEPLOYMENT_DIR/.env.production.template" "$DEPLOYMENT_DIR/.env"

        # Update values
        sed -i "s/^DB_NAME=.*/DB_NAME=${DB_NAME}/" "$DEPLOYMENT_DIR/.env"
        sed -i "s/^PORT=.*/PORT=${CURRENT_PORT}/" "$DEPLOYMENT_DIR/.env"

        print_warning "Please review and update .env with production credentials:"
        print_warning "  - SECRET_KEY (generate new secure key)"
        print_warning "  - DB_PASSWORD"
        print_warning "  - DB_HOST (if using remote database)"
    fi
fi

chown "${CURRENT_USER}:${CURRENT_GROUP}" "$DEPLOYMENT_DIR/.env"
chmod 600 "$DEPLOYMENT_DIR/.env"

print_success "Environment configured"

##############################################################################
# Step 7: Setup Python Environment
##############################################################################

print_header "Step 7: Setting Up Python Environment"

# Check if venv exists in old deployment
if [ -f "${DEPLOYMENT_DIR}.old/venv/bin/activate" ]; then
    print_info "Found existing virtual environment, removing..."
    rm -rf "${DEPLOYMENT_DIR}.old/venv"
fi

# Create new virtual environment
print_info "Creating virtual environment..."
sudo -u "$CURRENT_USER" python3 -m venv "$DEPLOYMENT_DIR/venv"

print_success "Virtual environment created"

# Install dependencies
print_info "Installing Python dependencies (this may take a few minutes)..."
sudo -u "$CURRENT_USER" "$DEPLOYMENT_DIR/venv/bin/pip" install --upgrade pip > /dev/null 2>&1
sudo -u "$CURRENT_USER" "$DEPLOYMENT_DIR/venv/bin/pip" install -r "$DEPLOYMENT_DIR/requirements.txt" > /dev/null 2>&1

print_success "Dependencies installed"

##############################################################################
# Step 8: Database Setup
##############################################################################

print_header "Step 8: Setting Up Database"

# Source environment to get DB credentials
if [ -f "$DEPLOYMENT_DIR/.env" ]; then
    export $(grep -v '^#' "$DEPLOYMENT_DIR/.env" | xargs)
fi

# Check if database exists
DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" 2>/dev/null || echo "")

if [ -z "$DB_EXISTS" ]; then
    print_info "Creating database: ${DB_NAME}..."
    sudo -u postgres createdb -O postgres "$DB_NAME"
    print_success "Database created"
else
    print_info "Database ${DB_NAME} already exists"
fi

# Check for database SQL file in package
DB_SQL_FILE=$(find "$DEPLOYMENT_DIR" -name "*.sql" -o -name "*database*.sql.gz" | head -1)

if [ ! -z "$DB_SQL_FILE" ] && [ -f "$DB_SQL_FILE" ]; then
    print_info "Found database file: $(basename $DB_SQL_FILE)"

    # Ask for confirmation
    echo ""
    read -p "$(echo -e ${YELLOW}WARNING: This will REPLACE all data in ${DB_NAME}. Continue? [y/N]:${NC} )" -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Restoring database from SQL file..."

        if [[ "$DB_SQL_FILE" == *.gz ]]; then
            gunzip -c "$DB_SQL_FILE" | sudo -u postgres psql "$DB_NAME" > /dev/null 2>&1
        else
            sudo -u postgres psql "$DB_NAME" < "$DB_SQL_FILE" > /dev/null 2>&1
        fi

        print_success "Database restored from SQL file"
    else
        print_warning "Skipped database restoration"
    fi
fi

# Run migrations
print_info "Running database migrations..."
cd "$DEPLOYMENT_DIR"
sudo -u "$CURRENT_USER" "$DEPLOYMENT_DIR/venv/bin/flask" db upgrade > /dev/null 2>&1 || {
    print_warning "Migration failed or no migrations needed"
}

print_success "Database setup complete"

##############################################################################
# Step 9: Update Systemd Service
##############################################################################

print_header "Step 9: Configuring Systemd Service"

# Check for existing service files
SERVICE_FILE=""
if [ -f "/etc/systemd/system/jalsarovar.service" ]; then
    SERVICE_FILE="/etc/systemd/system/jalsarovar.service"
    SERVICE_NAME="jalsarovar"
elif [ -f "/etc/systemd/system/lab4all.service" ]; then
    SERVICE_FILE="/etc/systemd/system/lab4all.service"
    SERVICE_NAME="lab4all"
fi

if [ ! -z "$SERVICE_FILE" ]; then
    print_info "Updating existing service: $SERVICE_NAME"

    # Update paths in service file
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=${DEPLOYMENT_DIR}|g" "$SERVICE_FILE"
    sed -i "s|ExecStart=.*/venv/bin/gunicorn|ExecStart=${DEPLOYMENT_DIR}/venv/bin/gunicorn|g" "$SERVICE_FILE"

    # Update user/group if changed
    sed -i "s|User=.*|User=${CURRENT_USER}|g" "$SERVICE_FILE"
    sed -i "s|Group=.*|Group=${CURRENT_GROUP}|g" "$SERVICE_FILE"

    print_success "Service file updated"
elif [ -f "$DEPLOYMENT_DIR/deployment/systemd/lab4all.service" ]; then
    print_info "Creating new systemd service..."

    # Copy and customize service file
    cp "$DEPLOYMENT_DIR/deployment/systemd/lab4all.service" "/etc/systemd/system/jalsarovar.service"

    # Update paths
    sed -i "s|WorkingDirectory=.*|WorkingDirectory=${DEPLOYMENT_DIR}|g" "/etc/systemd/system/jalsarovar.service"
    sed -i "s|ExecStart=.*/venv/bin/gunicorn|ExecStart=${DEPLOYMENT_DIR}/venv/bin/gunicorn|g" "/etc/systemd/system/jalsarovar.service"
    sed -i "s|User=.*|User=${CURRENT_USER}|g" "/etc/systemd/system/jalsarovar.service"
    sed -i "s|Group=.*|Group=${CURRENT_GROUP}|g" "/etc/systemd/system/jalsarovar.service"
    sed -i "s|PORT=.*|PORT=${CURRENT_PORT}|g" "/etc/systemd/system/jalsarovar.service"

    SERVICE_NAME="jalsarovar"
    print_success "Service file created"
else
    print_warning "No systemd service file found"
    SERVICE_NAME=""
fi

if [ ! -z "$SERVICE_NAME" ]; then
    print_info "Reloading systemd daemon..."
    systemctl daemon-reload
    print_success "Systemd configuration reloaded"
fi

##############################################################################
# Step 10: Update Nginx Configuration
##############################################################################

print_header "Step 10: Verifying Nginx Configuration"

NGINX_CONFIG="/etc/nginx/sites-available/jalsarovar"

if [ -f "$NGINX_CONFIG" ]; then
    print_success "Nginx configuration found: $NGINX_CONFIG"

    # Check if port matches
    NGINX_PORT=$(grep -oP 'proxy_pass.*localhost:\K\d+' "$NGINX_CONFIG" | head -1)

    if [ "$NGINX_PORT" != "$CURRENT_PORT" ]; then
        print_warning "Nginx is configured for port $NGINX_PORT but application uses $CURRENT_PORT"
        print_warning "Consider updating nginx configuration"
    else
        print_success "Nginx port matches application port: $CURRENT_PORT"
    fi

    # Test nginx configuration
    nginx -t > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        print_success "Nginx configuration is valid"
    else
        print_warning "Nginx configuration test failed - please check manually"
    fi
else
    print_warning "Nginx configuration not found at $NGINX_CONFIG"
    print_info "You may need to configure nginx manually"
fi

##############################################################################
# Step 11: Start Application
##############################################################################

print_header "Step 11: Starting Application"

if [ ! -z "$SERVICE_NAME" ]; then
    print_info "Enabling service: $SERVICE_NAME..."
    systemctl enable "$SERVICE_NAME" > /dev/null 2>&1

    print_info "Starting service: $SERVICE_NAME..."
    systemctl start "$SERVICE_NAME"

    sleep 3

    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service started successfully"
    else
        print_error "Service failed to start"
        print_info "Check logs with: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
else
    print_warning "No systemd service configured - manual start required"
fi

# Reload nginx
if [ -f "$NGINX_CONFIG" ]; then
    print_info "Reloading nginx..."
    nginx -s reload > /dev/null 2>&1 || systemctl reload nginx
    print_success "Nginx reloaded"
fi

##############################################################################
# Step 12: Verification
##############################################################################

print_header "Step 12: Post-Deployment Verification"

# Check if application responds
sleep 2

print_info "Testing application on port ${CURRENT_PORT}..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${CURRENT_PORT}/" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    print_success "Application is responding (HTTP $HTTP_CODE)"
else
    print_warning "Application returned HTTP $HTTP_CODE"
fi

# Database connection test
print_info "Testing database connection..."
cd "$DEPLOYMENT_DIR"
DB_TEST=$(sudo -u "$CURRENT_USER" "$DEPLOYMENT_DIR/venv/bin/python3" -c "
from app import create_app
app = create_app()
with app.app_context():
    from app import db
    from sqlalchemy import text
    try:
        db.session.execute(text('SELECT 1'))
        print('OK')
    except Exception as e:
        print(f'ERROR: {e}')
" 2>&1)

if [[ "$DB_TEST" == *"OK"* ]]; then
    print_success "Database connection successful"
else
    print_warning "Database connection test: $DB_TEST"
fi

# Cleanup
print_info "Cleaning up temporary files..."
rm -rf "$TEMP_EXTRACT"
print_success "Cleanup complete"

##############################################################################
# Deployment Summary
##############################################################################

print_header "Deployment Complete!"

echo -e "${GREEN}Summary:${NC}"
echo -e "  Deployment Directory: ${BLUE}${DEPLOYMENT_DIR}${NC}"
echo -e "  Application User:     ${BLUE}${CURRENT_USER}:${CURRENT_GROUP}${NC}"
echo -e "  Application Port:     ${BLUE}${CURRENT_PORT}${NC}"
echo -e "  Database:             ${BLUE}${DB_NAME}${NC}"
if [ ! -z "$SERVICE_NAME" ]; then
echo -e "  Systemd Service:      ${BLUE}${SERVICE_NAME}${NC}"
fi
echo ""

if [ "$FRESH_INSTALL" = false ]; then
echo -e "${CYAN}Backup Locations:${NC}"
echo -e "  Application: ${BACKUP_FILE}"
if [ ! -z "$DB_BACKUP_FILE" ]; then
echo -e "  Database:    ${DB_BACKUP_FILE}.gz"
fi
echo -e "  Old Version: ${DEPLOYMENT_DIR}.old"
echo ""
fi

echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Verify application: ${BLUE}https://www.jalsarovar.com${NC}"
echo -e "  2. Check service status: ${BLUE}systemctl status ${SERVICE_NAME}${NC}"
echo -e "  3. Monitor logs: ${BLUE}journalctl -u ${SERVICE_NAME} -f${NC}"
if [ "$FRESH_INSTALL" = false ]; then
echo -e "  4. If issues occur, rollback with: ${BLUE}./rollback_deployment.sh${NC}"
fi
echo ""

print_success "Deployment completed successfully!"
echo ""
