#!/bin/bash
# ============================================================================
# Jal Sarovar - Database Restoration Script (Run on Remote Server)
# Restores database dump to demo.jalsarovar.com
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}Jal Sarovar Database Restoration${NC}"
echo -e "${GREEN}For demo.jalsarovar.com${NC}"
echo ""

# Check if running on remote server
if [ ! -d "/var/www/jalsarovar_demo" ]; then
    echo -e "${YELLOW}Warning: Demo application directory not found at /var/www/jalsarovar_demo${NC}"
    echo "This script should be run on the remote server after deployment."
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Configuration
DUMP_DIR="/tmp"
BACKUP_DIR="/var/backups/jalsarovar_demo"

# Find the most recent dump file
DUMP_FILE=$(ls -t ${DUMP_DIR}/jalsarovar_db_*.sql.gz 2>/dev/null | head -1)

if [ -z "$DUMP_FILE" ]; then
    echo -e "${RED}Error: No database dump file found in ${DUMP_DIR}/${NC}"
    echo ""
    echo "Expected filename pattern: jalsarovar_db_YYYYMMDD_HHMMSS.sql.gz"
    echo ""
    echo "Please transfer the database dump first:"
    echo "  scp backups/jalsarovar_db_*.sql.gz user@demo.jalsarovar.com:/tmp/"
    echo ""
    exit 1
fi

echo -e "${BLUE}Found dump file: ${DUMP_FILE}${NC}"
DUMP_SIZE=$(du -h ${DUMP_FILE} | cut -f1)
echo "Dump file size: ${DUMP_SIZE}"
echo ""

# Prompt for database credentials
echo -e "${YELLOW}Database Configuration${NC}"
echo "Enter database credentials (these should match your demo deployment)"
echo ""

read -p "Database Host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-localhost}

read -p "Database Port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-5432}

read -p "Database Name [jal_sarovar_demo]: " DB_NAME
DB_NAME=${DB_NAME:-jal_sarovar_demo}

read -p "Database User [postgres]: " DB_USER
DB_USER=${DB_USER:-postgres}

read -sp "Database Password: " DB_PASSWORD
echo ""
echo ""

# Test database connection
echo -e "${YELLOW}Testing database connection...${NC}"
if PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo "Please check your credentials and ensure PostgreSQL is running."
    exit 1
fi

# Check if database exists
echo ""
echo -e "${YELLOW}Checking for existing database...${NC}"
DB_EXISTS=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")

if [ "$DB_EXISTS" = "1" ]; then
    echo -e "${YELLOW}Database '${DB_NAME}' already exists${NC}"
    echo ""

    # Get database statistics
    TABLE_COUNT=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")
    DB_SIZE=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -tAc "SELECT pg_size_pretty(pg_database_size('${DB_NAME}'))" 2>/dev/null || echo "unknown")

    echo "Existing database statistics:"
    echo "  Tables: ${TABLE_COUNT}"
    echo "  Size: ${DB_SIZE}"
    echo ""

    # Create backup directory
    mkdir -p ${BACKUP_DIR}

    # Backup existing database
    BACKUP_FILE="${BACKUP_DIR}/jal_sarovar_demo_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
    echo -e "${YELLOW}Creating backup of existing database...${NC}"
    echo "Backup location: ${BACKUP_FILE}"

    PGPASSWORD=${DB_PASSWORD} pg_dump \
        -h ${DB_HOST} \
        -p ${DB_PORT} \
        -U ${DB_USER} \
        -d ${DB_NAME} \
        --clean \
        --if-exists | gzip > ${BACKUP_FILE}

    if [ $? -eq 0 ]; then
        BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
        echo -e "${GREEN}✓ Backup created successfully (${BACKUP_SIZE})${NC}"
    else
        echo -e "${RED}✗ Backup failed${NC}"
        exit 1
    fi

    echo ""
    echo -e "${RED}⚠️  WARNING: This will REPLACE all data in '${DB_NAME}' database${NC}"
    read -p "Continue with restoration? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Restoration cancelled."
        exit 0
    fi
else
    echo -e "${GREEN}Database '${DB_NAME}' does not exist (will be created)${NC}"
fi

# Decompress dump file if needed
echo ""
echo -e "${YELLOW}Preparing dump file...${NC}"
SQL_FILE="${DUMP_FILE%.gz}"

if [ "${DUMP_FILE}" != "${SQL_FILE}" ]; then
    echo "Decompressing dump file..."
    gunzip -k ${DUMP_FILE}

    if [ ! -f "${SQL_FILE}" ]; then
        echo -e "${RED}✗ Decompression failed${NC}"
        exit 1
    fi

    SQL_SIZE=$(du -h ${SQL_FILE} | cut -f1)
    echo -e "${GREEN}✓ Decompression successful (${SQL_SIZE})${NC}"
else
    SQL_FILE="${DUMP_FILE}"
fi

# Drop existing database
if [ "$DB_EXISTS" = "1" ]; then
    echo ""
    echo -e "${YELLOW}Dropping existing database...${NC}"

    # Terminate existing connections
    PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "
    SELECT pg_terminate_backend(pg_stat_activity.pid)
    FROM pg_stat_activity
    WHERE pg_stat_activity.datname = '${DB_NAME}'
    AND pid <> pg_backend_pid();" > /dev/null 2>&1

    PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database dropped${NC}"
    else
        echo -e "${RED}✗ Failed to drop database${NC}"
        exit 1
    fi
fi

# Create fresh database
echo ""
echo -e "${YELLOW}Creating fresh database...${NC}"
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database created${NC}"
else
    echo -e "${RED}✗ Failed to create database${NC}"
    exit 1
fi

# Restore database
echo ""
echo -e "${YELLOW}Restoring database from dump...${NC}"
echo "This may take a few minutes depending on database size..."
echo ""

PGPASSWORD=${DB_PASSWORD} psql \
    -h ${DB_HOST} \
    -p ${DB_PORT} \
    -U ${DB_USER} \
    -d ${DB_NAME} \
    -v ON_ERROR_STOP=1 \
    < ${SQL_FILE} 2>&1 | grep -v "^CREATE\|^ALTER\|^COPY\|^SET\|^--" | grep -v "^\s*$" || true

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
else
    echo -e "${RED}✗ Database restoration failed${NC}"
    echo "Check the error messages above for details."
    exit 1
fi

# Get restored database statistics
echo ""
echo -e "${YELLOW}Verifying restoration...${NC}"
RESTORED_TABLES=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
RESTORED_SIZE=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -tAc "SELECT pg_size_pretty(pg_database_size('${DB_NAME}'))")

echo "Restored database statistics:"
echo "  Tables: ${RESTORED_TABLES}"
echo "  Size: ${RESTORED_SIZE}"
echo ""

# Check key tables
echo "Record counts in key tables:"
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "
SELECT
    'sites' as table_name, COUNT(*) as records FROM sites
UNION ALL
SELECT 'samples', COUNT(*) FROM samples
UNION ALL
SELECT 'test_results', COUNT(*) FROM test_results
UNION ALL
SELECT 'analyses', COUNT(*) FROM analyses
UNION ALL
SELECT 'users', COUNT(*) FROM users
ORDER BY table_name;" 2>/dev/null || echo "Note: Some tables may not exist yet"

# Run database migrations
if [ -d "/var/www/jalsarovar_demo/jalsarovar" ]; then
    echo ""
    echo -e "${YELLOW}Running database migrations...${NC}"
    cd /var/www/jalsarovar_demo/jalsarovar

    if sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade 2>&1; then
        echo -e "${GREEN}✓ Migrations completed${NC}"
    else
        echo -e "${YELLOW}⚠ Migrations failed or not needed${NC}"
    fi

    # Restart demo application
    echo ""
    echo -e "${YELLOW}Restarting demo application...${NC}"
    if sudo systemctl restart jalsarovar-demo 2>&1; then
        echo -e "${GREEN}✓ Application restarted${NC}"

        # Wait a moment for service to start
        sleep 2

        # Check service status
        if systemctl is-active --quiet jalsarovar-demo; then
            echo -e "${GREEN}✓ Service is running${NC}"
        else
            echo -e "${RED}✗ Service failed to start${NC}"
            echo "Check logs: sudo journalctl -u jalsarovar-demo -n 50"
        fi
    else
        echo -e "${YELLOW}⚠ Could not restart application (may need to do manually)${NC}"
    fi

    # Test application health
    echo ""
    echo -e "${YELLOW}Testing application health...${NC}"
    sleep 1

    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Application is responding${NC}"
        curl -s http://localhost:8001/health | python3 -m json.tool 2>/dev/null || echo "Health check passed"
    else
        echo -e "${YELLOW}⚠ Application health check failed${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}⚠ Demo application directory not found${NC}"
    echo "You may need to run migrations and restart the application manually:"
    echo "  cd /var/www/jalsarovar_demo/jalsarovar"
    echo "  sudo -u jalsarovar-demo /var/www/jalsarovar_demo/venv/bin/flask db upgrade"
    echo "  sudo systemctl restart jalsarovar-demo"
fi

# Cleanup
echo ""
echo -e "${YELLOW}Cleaning up...${NC}"
if [ -f "${SQL_FILE}" ] && [ "${SQL_FILE}" != "${DUMP_FILE}" ]; then
    rm -f ${SQL_FILE}
    echo "✓ Removed decompressed SQL file"
fi

# Summary
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Database Restoration Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Summary:"
echo "  Database: ${DB_NAME}"
echo "  Tables: ${RESTORED_TABLES}"
echo "  Size: ${RESTORED_SIZE}"
if [ "$DB_EXISTS" = "1" ]; then
    echo "  Backup: ${BACKUP_FILE}"
fi
echo ""
echo "Next steps:"
echo "  1. Test at: http://demo.jalsarovar.com"
echo "  2. Login with your credentials"
echo "  3. Verify sites and samples data"
echo ""
echo "Troubleshooting:"
echo "  View logs: sudo journalctl -u jalsarovar-demo -f"
echo "  Check status: sudo systemctl status jalsarovar-demo"
echo "  Restart: sudo systemctl restart jalsarovar-demo"
echo ""
