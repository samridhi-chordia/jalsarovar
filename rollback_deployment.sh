#!/bin/bash

##############################################################################
# Jal Sarovar - Deployment Rollback Script
# Rolls back to previous version in case of deployment issues
##############################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DEPLOYMENT_DIR="/var/www/jalsarovar"
BACKUP_DIR="/var/backups/jalsarovar"

echo -e "${RED}========================================${NC}"
echo -e "${RED}Jal Sarovar - Deployment Rollback${NC}"
echo -e "${RED}========================================${NC}"
echo ""

# Check root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}✗${NC} This script must be run as root or with sudo"
    exit 1
fi

# Check if old version exists
if [ ! -d "${DEPLOYMENT_DIR}.old" ]; then
    echo -e "${RED}✗${NC} No previous version found at ${DEPLOYMENT_DIR}.old"
    exit 1
fi

echo -e "${YELLOW}⚠${NC} This will restore the previous version of Jal Sarovar"
echo ""
echo "Current version will be backed up before rollback."
echo ""
read -p "$(echo -e ${YELLOW}Continue with rollback? [y/N]:${NC} )" -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Rollback cancelled"
    exit 0
fi

echo ""
echo -e "${BLUE}Starting rollback...${NC}"
echo ""

# Get service name
if systemctl is-active --quiet jalsarovar; then
    SERVICE_NAME="jalsarovar"
elif systemctl is-active --quiet lab4all; then
    SERVICE_NAME="lab4all"
else
    SERVICE_NAME=""
fi

# Stop service
if [ ! -z "$SERVICE_NAME" ]; then
    echo -e "${BLUE}→${NC} Stopping $SERVICE_NAME service..."
    systemctl stop "$SERVICE_NAME"
    echo -e "${GREEN}✓${NC} Service stopped"
fi

# Backup current failed version
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo -e "${BLUE}→${NC} Backing up failed version..."
mv "$DEPLOYMENT_DIR" "${DEPLOYMENT_DIR}.failed_${TIMESTAMP}"
echo -e "${GREEN}✓${NC} Failed version saved: ${DEPLOYMENT_DIR}.failed_${TIMESTAMP}"

# Restore old version
echo -e "${BLUE}→${NC} Restoring previous version..."
mv "${DEPLOYMENT_DIR}.old" "$DEPLOYMENT_DIR"
echo -e "${GREEN}✓${NC} Previous version restored"

# Start service
if [ ! -z "$SERVICE_NAME" ]; then
    echo -e "${BLUE}→${NC} Starting $SERVICE_NAME service..."
    systemctl start "$SERVICE_NAME"

    sleep 3

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo -e "${GREEN}✓${NC} Service started successfully"
    else
        echo -e "${RED}✗${NC} Service failed to start"
        echo "Check logs: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
fi

# Reload nginx
echo -e "${BLUE}→${NC} Reloading nginx..."
systemctl reload nginx || nginx -s reload
echo -e "${GREEN}✓${NC} Nginx reloaded"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Rollback Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Previous version has been restored to: ${BLUE}${DEPLOYMENT_DIR}${NC}"
echo -e "Failed version saved to: ${BLUE}${DEPLOYMENT_DIR}.failed_${TIMESTAMP}${NC}"
echo ""
echo "Verify application: https://www.jalsarovar.com"
echo ""
