#!/bin/bash
# ============================================================================
# Jal Sarovar - Create Database Dump for Transfer
# Creates a compressed SQL dump of the local database
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Jal Sarovar Database Dump Creator${NC}"
echo -e "${GREEN}For transfer to demo.jalsarovar.com${NC}"
echo ""

# Load environment variables from .env file
ENV_FILE="/Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found at $ENV_FILE${NC}"
    exit 1
fi

# Parse .env file
export $(grep -v '^#' $ENV_FILE | grep -E '^(DB_HOST|DB_PORT|DB_NAME|DB_USER|DB_PASSWORD)=' | xargs)

# Configuration
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_DIR="/Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar/backups"
DUMP_FILE="${DUMP_DIR}/jalsarovar_db_${TIMESTAMP}.sql"
COMPRESSED_FILE="${DUMP_FILE}.gz"

# Create backups directory if it doesn't exist
mkdir -p ${DUMP_DIR}

echo "Database Configuration:"
echo "  Host: ${DB_HOST}"
echo "  Port: ${DB_PORT}"
echo "  Database: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo ""

# Test database connection first
echo -e "${YELLOW}Testing database connection...${NC}"
if PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo "Please check your database credentials and ensure PostgreSQL is running."
    exit 1
fi

# Get database size and statistics
echo ""
echo -e "${YELLOW}Gathering database statistics...${NC}"
DB_SIZE=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT pg_size_pretty(pg_database_size('${DB_NAME}'))")
TABLE_COUNT=$(PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")

echo "  Database size: ${DB_SIZE}"
echo "  Number of tables: ${TABLE_COUNT}"
echo ""

# Create database dump
echo -e "${YELLOW}Creating database dump...${NC}"
echo "This may take a few minutes depending on database size..."

PGPASSWORD=${DB_PASSWORD} pg_dump \
    -h ${DB_HOST} \
    -p ${DB_PORT} \
    -U ${DB_USER} \
    -d ${DB_NAME} \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --format=plain \
    --file=${DUMP_FILE}

if [ -f "${DUMP_FILE}" ] && [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database dump created successfully${NC}"
else
    echo -e "${RED}✗ Database dump failed${NC}"
    exit 1
fi

# Get dump file size
DUMP_SIZE=$(du -h ${DUMP_FILE} | cut -f1)
echo "  Dump file size: ${DUMP_SIZE}"

# Compress the dump
echo ""
echo -e "${YELLOW}Compressing dump file...${NC}"
gzip ${DUMP_FILE}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Compression successful${NC}"
else
    echo -e "${RED}✗ Compression failed${NC}"
    exit 1
fi

# Get compressed file size
COMPRESSED_SIZE=$(du -h ${COMPRESSED_FILE} | cut -f1)

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Database dump created successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Dump file location: ${COMPRESSED_FILE}"
echo "Original size: ${DUMP_SIZE}"
echo "Compressed size: ${COMPRESSED_SIZE}"
echo ""
echo "Next steps:"
echo ""
echo "1. Transfer to remote server:"
echo "   scp ${COMPRESSED_FILE} user@demo.jalsarovar.com:/tmp/"
echo ""
echo "   Or if using main server:"
echo "   scp ${COMPRESSED_FILE} user@jalsarovar.com:/tmp/"
echo ""
echo "2. SSH to server and restore:"
echo "   ssh user@demo.jalsarovar.com"
echo "   (Follow the restoration steps in RESTORE_DATABASE.md)"
echo ""
echo "For detailed restoration instructions, see:"
echo "   deployment/RESTORE_DATABASE.md"
echo ""
