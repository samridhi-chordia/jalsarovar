#!/bin/bash
# ============================================================================
# Jal Sarovar - Create Deployment Package
# Creates a compressed tar file ready for deployment to demo.jalsarovar.com
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Jal Sarovar Deployment Package Creator${NC}"
echo -e "${GREEN}Target: demo.jalsarovar.com${NC}"
echo ""

# Configuration
APP_DIR="/Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="jalsarovar_${TIMESTAMP}.tar.gz"
TEMP_DIR="/tmp/jalsarovar_deploy_${TIMESTAMP}"

echo "Source directory: ${APP_DIR}"
echo "Package name: ${PACKAGE_NAME}"
echo ""

# Create temporary directory
echo -e "${YELLOW}Creating temporary directory...${NC}"
mkdir -p ${TEMP_DIR}

# Copy files (excluding unnecessary files)
echo -e "${YELLOW}Copying application files...${NC}"
rsync -av --progress \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='.gitignore' \
    --exclude='*.log' \
    --exclude='logs/*' \
    --exclude='*.db' \
    --exclude='*.sqlite' \
    --exclude='*.sqlite3' \
    --exclude='venv' \
    --exclude='env' \
    --exclude='ENV' \
    --exclude='.venv' \
    --exclude='*.egg-info' \
    --exclude='.pytest_cache' \
    --exclude='.coverage' \
    --exclude='htmlcov' \
    --exclude='.DS_Store' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='*.swp' \
    --exclude='*.swo' \
    --exclude='uploads/*' \
    --exclude='!uploads/.gitkeep' \
    --exclude='backups/*' \
    --exclude='docs/*.md' \
    --exclude='docs/*.tsv' \
    --exclude='scripts/populate_data.py' \
    --exclude='scripts/test_*.py' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='.env.development' \
    ${APP_DIR}/ ${TEMP_DIR}/

# Create necessary directories
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p ${TEMP_DIR}/uploads
mkdir -p ${TEMP_DIR}/logs
mkdir -p ${TEMP_DIR}/backups
touch ${TEMP_DIR}/uploads/.gitkeep
touch ${TEMP_DIR}/logs/.gitkeep
touch ${TEMP_DIR}/backups/.gitkeep

# Note: app/ml/models/ will be created by rsync when copying model files

# Copy .env template (not the actual .env)
if [ -f "${APP_DIR}/.env.production.template" ]; then
    cp ${APP_DIR}/.env.production.template ${TEMP_DIR}/.env.production.template
fi

# Create README for deployment
cat > ${TEMP_DIR}/DEPLOY_README.txt << 'EOF'
Jal Sarovar Water Quality Management System - Deployment Package
================================================================

This package contains the Jal Sarovar application ready for deployment
to demo.jalsarovar.com subdomain.

IMPORTANT: Before deploying, ensure you have:
1. Python 3.11 installed
2. PostgreSQL 15 installed and running
3. Nginx installed
4. Root or sudo access
5. DNS configured (demo.jalsarovar.com pointing to your server)

Quick Deployment Steps:
-----------------------

1. Extract this package:
   tar -xzf jalsarovar_TIMESTAMP.tar.gz
   cd jalsarovar_TIMESTAMP

2. Run the remote setup script:
   sudo bash deployment/scripts/remote_setup.sh

3. Follow the prompts to configure:
   - Domain: demo.jalsarovar.com
   - Database credentials
   - Application settings
   - SSL certificate (optional)

For detailed instructions, see:
deployment/DEMO_DEPLOYMENT.md

Support:
--------
For issues or questions, refer to the documentation in the deployment/ directory.

EOF

# Create tarball
echo -e "${YELLOW}Creating compressed tar package...${NC}"
cd $(dirname ${TEMP_DIR})
tar -czf ${APP_DIR}/${PACKAGE_NAME} $(basename ${TEMP_DIR})

# Cleanup
echo -e "${YELLOW}Cleaning up temporary files...${NC}"
rm -rf ${TEMP_DIR}

# Get file size
PACKAGE_SIZE=$(du -h ${APP_DIR}/${PACKAGE_NAME} | cut -f1)

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Package created successfully!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Package location: ${APP_DIR}/${PACKAGE_NAME}"
echo "Package size: ${PACKAGE_SIZE}"
echo ""
echo "Next steps:"
echo "1. Transfer to demo server:"
echo "   scp ${PACKAGE_NAME} user@demo.jalsarovar.com:/tmp/"
echo ""
echo "   Or if using main server with subdomain:"
echo "   scp ${PACKAGE_NAME} user@jalsarovar.com:/tmp/"
echo ""
echo "2. SSH to server:"
echo "   ssh user@demo.jalsarovar.com"
echo "   (or: ssh user@jalsarovar.com)"
echo ""
echo "3. Extract and deploy:"
echo "   cd /tmp"
echo "   tar -xzf ${PACKAGE_NAME}"
echo "   cd $(basename ${TEMP_DIR})"
echo "   sudo bash deployment/scripts/remote_setup.sh"
echo ""
