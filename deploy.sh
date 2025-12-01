#!/bin/bash
#===============================================================================
# Jal Sarovar - Production Deployment Script
# Water Quality Monitoring and Management System
#===============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Configuration variables
APP_NAME="jalsarovar"
APP_DIR="/var/www/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
DB_DIR="${APP_DIR}/instance"
BACKUP_DIR="${APP_DIR}/backups"
LOG_DIR="${APP_DIR}/logs"
UPLOAD_DIR="${APP_DIR}/uploads"

# System user for running the application
APP_USER="${APP_USER:-www-data}"

#===============================================================================
# Pre-flight checks
#===============================================================================
preflight_checks() {
    log_info "Running pre-flight checks..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_info "Python version: ${PYTHON_VERSION}"

    # Check for required packages
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is not installed"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}

#===============================================================================
# Install system dependencies
#===============================================================================
install_dependencies() {
    log_info "Installing system dependencies..."

    # Update package list
    apt-get update -qq

    # Install required packages
    apt-get install -y -qq \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        nginx \
        postgresql \
        postgresql-contrib \
        libpq-dev \
        supervisor \
        sqlite3 \
        gzip \
        curl

    log_success "System dependencies installed"
}

#===============================================================================
# Create application directory structure
#===============================================================================
create_directories() {
    log_info "Creating application directory structure..."

    mkdir -p "${APP_DIR}"
    mkdir -p "${DB_DIR}"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${LOG_DIR}"
    mkdir -p "${UPLOAD_DIR}"

    log_success "Directory structure created"
}

#===============================================================================
# Copy application files
#===============================================================================
deploy_application() {
    log_info "Deploying application files..."

    # Get the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    # Copy application files
    cp -r "${SCRIPT_DIR}/app" "${APP_DIR}/"
    cp "${SCRIPT_DIR}/app.py" "${APP_DIR}/"
    cp "${SCRIPT_DIR}/config.py" "${APP_DIR}/"
    cp "${SCRIPT_DIR}/requirements.txt" "${APP_DIR}/"

    log_success "Application files deployed"
}

#===============================================================================
# Setup virtual environment and install dependencies
#===============================================================================
setup_venv() {
    log_info "Setting up Python virtual environment..."

    cd "${APP_DIR}"

    # Create virtual environment
    python3 -m venv "${VENV_DIR}"

    # Activate virtual environment
    source "${VENV_DIR}/bin/activate"

    # Upgrade pip
    pip install --upgrade pip --quiet

    # Install application dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt --quiet

    deactivate

    log_success "Virtual environment setup complete"
}

#===============================================================================
# Setup database
#===============================================================================
setup_database() {
    log_info "Setting up database..."

    # Get the directory where this script is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

    # Check if database SQL file exists
    if [ -f "${SCRIPT_DIR}/database/jalsarovar_production.sql.gz" ]; then
        log_info "Importing database from SQL file..."

        # Extract and import SQL
        gunzip -c "${SCRIPT_DIR}/database/jalsarovar_production.sql.gz" | \
            sqlite3 "${DB_DIR}/jalsarovar.db"

        log_success "Database imported successfully"
    else
        log_warning "No database file found. Creating empty database..."

        # Initialize empty database with Flask-Migrate
        cd "${APP_DIR}"
        source "${VENV_DIR}/bin/activate"
        export FLASK_APP=app.py
        flask db upgrade
        deactivate

        log_success "Empty database created"
    fi

    # Set database permissions
    chmod 660 "${DB_DIR}/jalsarovar.db"
}

#===============================================================================
# Create production .env file
#===============================================================================
create_env_file() {
    log_info "Creating production environment configuration..."

    # Generate random secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    cat > "${APP_DIR}/.env" <<EOF
# Jal Sarovar Production Configuration
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=${SECRET_KEY}
DATABASE_URL=sqlite:///${DB_DIR}/jalsarovar.db
DEBUG=False
ML_MODELS_PATH=app/ml/models
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=${UPLOAD_DIR}
LOG_LEVEL=INFO
EOF

    chmod 600 "${APP_DIR}/.env"

    log_success "Environment configuration created"
}

#===============================================================================
# Configure Nginx
#===============================================================================
configure_nginx() {
    log_info "Configuring Nginx..."

    cat > "/etc/nginx/sites-available/${APP_NAME}" <<'EOF'
server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static {
        alias /var/www/jalsarovar/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /var/www/jalsarovar/uploads;
        internal;
    }
}
EOF

    # Enable site
    ln -sf "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/${APP_NAME}"

    # Remove default site if exists
    rm -f /etc/nginx/sites-enabled/default

    # Test Nginx configuration
    nginx -t

    # Reload Nginx
    systemctl reload nginx
    systemctl enable nginx

    log_success "Nginx configured"
}

#===============================================================================
# Configure Supervisor for Gunicorn
#===============================================================================
configure_supervisor() {
    log_info "Configuring Supervisor..."

    cat > "/etc/supervisor/conf.d/${APP_NAME}.conf" <<EOF
[program:${APP_NAME}]
command=${VENV_DIR}/bin/gunicorn --bind 127.0.0.1:8000 --workers 4 --threads 2 --timeout 60 --access-logfile ${LOG_DIR}/access.log --error-logfile ${LOG_DIR}/error.log app:app
directory=${APP_DIR}
user=${APP_USER}
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=${LOG_DIR}/supervisor_error.log
stdout_logfile=${LOG_DIR}/supervisor_output.log
environment=FLASK_APP="app.py",FLASK_ENV="production"
EOF

    # Reload supervisor
    supervisorctl reread
    supervisorctl update
    supervisorctl restart "${APP_NAME}"

    log_success "Supervisor configured"
}

#===============================================================================
# Set file permissions
#===============================================================================
set_permissions() {
    log_info "Setting file permissions..."

    # Change ownership
    chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

    # Set directory permissions
    chmod 755 "${APP_DIR}"
    chmod 755 "${DB_DIR}"
    chmod 755 "${BACKUP_DIR}"
    chmod 755 "${LOG_DIR}"
    chmod 755 "${UPLOAD_DIR}"

    # Set file permissions
    find "${APP_DIR}" -type f -exec chmod 644 {} \;
    find "${APP_DIR}" -type d -exec chmod 755 {} \;

    # Make scripts executable
    chmod +x "${APP_DIR}"/*.sh 2>/dev/null || true

    log_success "File permissions set"
}

#===============================================================================
# Create backup script
#===============================================================================
create_backup_script() {
    log_info "Creating backup script..."

    cat > "${APP_DIR}/backup.sh" <<'EOF'
#!/bin/bash
# Jal Sarovar Database Backup Script

BACKUP_DIR="/var/www/jalsarovar/backups"
DB_FILE="/var/www/jalsarovar/instance/jalsarovar.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/jalsarovar_backup_${TIMESTAMP}.sql.gz"

# Create backup
sqlite3 "${DB_FILE}" ".dump" | gzip > "${BACKUP_FILE}"

# Keep only last 10 backups
ls -t ${BACKUP_DIR}/jalsarovar_backup_*.sql.gz | tail -n +11 | xargs rm -f 2>/dev/null || true

echo "Backup created: ${BACKUP_FILE}"
EOF

    chmod +x "${APP_DIR}/backup.sh"

    # Add cron job for daily backups (2 AM)
    (crontab -u "${APP_USER}" -l 2>/dev/null; echo "0 2 * * * ${APP_DIR}/backup.sh") | \
        crontab -u "${APP_USER}" -

    log_success "Backup script created"
}

#===============================================================================
# Health check
#===============================================================================
health_check() {
    log_info "Running health check..."

    sleep 3  # Wait for services to start

    # Check if Gunicorn is running
    if supervisorctl status "${APP_NAME}" | grep -q "RUNNING"; then
        log_success "Gunicorn is running"
    else
        log_error "Gunicorn is not running"
        return 1
    fi

    # Check if application responds
    if curl -f -s http://localhost:8000/ > /dev/null; then
        log_success "Application is responding"
    else
        log_warning "Application is not responding yet"
    fi

    # Check if Nginx is running
    if systemctl is-active --quiet nginx; then
        log_success "Nginx is running"
    else
        log_error "Nginx is not running"
        return 1
    fi

    log_success "Health check passed"
}

#===============================================================================
# Display deployment summary
#===============================================================================
display_summary() {
    echo ""
    echo "==============================================================================="
    echo "  Jal Sarovar - Deployment Summary"
    echo "==============================================================================="
    echo ""
    echo "Application Directory: ${APP_DIR}"
    echo "Database Location: ${DB_DIR}/jalsarovar.db"
    echo "Logs Directory: ${LOG_DIR}"
    echo "Uploads Directory: ${UPLOAD_DIR}"
    echo "Backups Directory: ${BACKUP_DIR}"
    echo ""
    echo "Application URL: http://$(hostname -I | awk '{print $1}')/"
    echo ""
    echo "Default Credentials:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    echo "Important Commands:"
    echo "  - Check status: supervisorctl status ${APP_NAME}"
    echo "  - Restart app:  supervisorctl restart ${APP_NAME}"
    echo "  - View logs:    tail -f ${LOG_DIR}/error.log"
    echo "  - Backup DB:    ${APP_DIR}/backup.sh"
    echo ""
    echo "==============================================================================="
    echo ""
}

#===============================================================================
# Main deployment flow
#===============================================================================
main() {
    echo ""
    echo "==============================================================================="
    echo "  Jal Sarovar - Production Deployment"
    echo "  Water Quality Monitoring and Management System"
    echo "==============================================================================="
    echo ""

    preflight_checks
    install_dependencies
    create_directories
    deploy_application
    setup_venv
    setup_database
    create_env_file
    configure_nginx
    configure_supervisor
    set_permissions
    create_backup_script
    health_check
    display_summary

    log_success "Deployment complete!"
    echo ""
}

# Run main function
main "$@"
