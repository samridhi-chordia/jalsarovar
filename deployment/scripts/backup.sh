#!/bin/bash
# ============================================================================
# Lab4All Web Application - Database Backup Script
# Creates compressed PostgreSQL backups with rotation
# ============================================================================

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/lab4all_backup_${TIMESTAMP}.sql.gz"

# Database connection (from environment variables)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-jal_sarovar_prod}"
DB_USER="${DB_USER:-postgres}"
# DB_PASSWORD is read from environment

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Lab4All Database Backup Script${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Backup directory: ${BACKUP_DIR}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Check if database is accessible
echo -e "${YELLOW}Checking database connection...${NC}"
if ! PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to database${NC}"
    echo "Host: ${DB_HOST}:${DB_PORT}"
    echo "Database: ${DB_NAME}"
    echo "User: ${DB_USER}"
    exit 1
fi

echo -e "${GREEN}✓ Database connection successful${NC}"
echo ""

# Create backup
echo -e "${YELLOW}Creating database backup...${NC}"
PGPASSWORD=${DB_PASSWORD} pg_dump \
    -h ${DB_HOST} \
    -p ${DB_PORT} \
    -U ${DB_USER} \
    -d ${DB_NAME} \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    2>&1 | gzip > ${BACKUP_FILE}

# Check if backup was created successfully
if [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  File: ${BACKUP_FILE}"
    echo "  Size: ${BACKUP_SIZE}"
else
    echo -e "${RED}ERROR: Backup file not created${NC}"
    exit 1
fi

# Verify backup integrity
echo ""
echo -e "${YELLOW}Verifying backup integrity...${NC}"
if gunzip -t ${BACKUP_FILE} 2>/dev/null; then
    echo -e "${GREEN}✓ Backup file is valid${NC}"
else
    echo -e "${RED}ERROR: Backup file is corrupted${NC}"
    exit 1
fi

# Delete old backups
echo ""
echo -e "${YELLOW}Cleaning up old backups (older than ${RETENTION_DAYS} days)...${NC}"
DELETED_COUNT=$(find ${BACKUP_DIR} -name "lab4all_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo -e "${GREEN}✓ Deleted ${DELETED_COUNT} old backup(s)${NC}"

# List current backups
echo ""
echo -e "${YELLOW}Current backups:${NC}"
find ${BACKUP_DIR} -name "lab4all_backup_*.sql.gz" -type f -exec ls -lh {} \; | awk '{print "  " $9 " (" $5 ")"}'

# Summary
echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Backup completed successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Backup file: ${BACKUP_FILE}"
echo "Retention policy: ${RETENTION_DAYS} days"
echo ""
echo "To restore this backup:"
echo "  gunzip -c ${BACKUP_FILE} | PGPASSWORD=\$DB_PASSWORD psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME}"
echo ""

# Optional: Upload to cloud storage
if [ -n "${S3_BUCKET}" ]; then
    echo -e "${YELLOW}Uploading to S3...${NC}"
    aws s3 cp ${BACKUP_FILE} s3://${S3_BUCKET}/backups/ && \
    echo -e "${GREEN}✓ Uploaded to S3${NC}"
fi

if [ -n "${GCS_BUCKET}" ]; then
    echo -e "${YELLOW}Uploading to Google Cloud Storage...${NC}"
    gsutil cp ${BACKUP_FILE} gs://${GCS_BUCKET}/backups/ && \
    echo -e "${GREEN}✓ Uploaded to GCS${NC}"
fi

if [ -n "${AZURE_STORAGE_ACCOUNT}" ] && [ -n "${AZURE_STORAGE_KEY}" ]; then
    echo -e "${YELLOW}Uploading to Azure Blob Storage...${NC}"
    az storage blob upload \
        --account-name ${AZURE_STORAGE_ACCOUNT} \
        --account-key ${AZURE_STORAGE_KEY} \
        --container-name backups \
        --file ${BACKUP_FILE} \
        --name $(basename ${BACKUP_FILE}) && \
    echo -e "${GREEN}✓ Uploaded to Azure${NC}"
fi
