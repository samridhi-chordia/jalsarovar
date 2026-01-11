#!/bin/bash
# ============================================================================
# Lab4All Web Application - Azure Deployment Script
# Deploys the application to Azure using Container Instances and PostgreSQL
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-production}"
AZURE_REGION="${AZURE_REGION:-centralindia}"
RESOURCE_GROUP="${ENVIRONMENT}-lab4all-rg"
ACR_NAME="${ENVIRONMENT}lab4allacr"
APP_NAME="${ENVIRONMENT}-lab4all"
DB_SERVER_NAME="${ENVIRONMENT}-lab4all-db"

echo -e "${GREEN}Lab4All Azure Deployment Script${NC}"
echo "Environment: ${ENVIRONMENT}"
echo "Azure Region: ${AZURE_REGION}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}ERROR: Azure CLI is not installed${NC}"
    echo "Install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    echo "Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Azure login
if ! az account show &> /dev/null; then
    echo -e "${RED}ERROR: Not logged into Azure${NC}"
    echo "Run: az login"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Prompt for sensitive parameters
read -sp "Enter database admin password (min 8 characters): " DB_PASSWORD
echo ""
read -sp "Enter Flask secret key (min 32 characters): " SECRET_KEY
echo ""

if [ ${#DB_PASSWORD} -lt 8 ]; then
    echo -e "${RED}ERROR: Database password must be at least 8 characters${NC}"
    exit 1
fi

if [ ${#SECRET_KEY} -lt 32 ]; then
    echo -e "${RED}ERROR: Secret key must be at least 32 characters${NC}"
    exit 1
fi

# Step 1: Create Resource Group
echo -e "${YELLOW}Step 1: Creating Resource Group...${NC}"
az group create \
    --name ${RESOURCE_GROUP} \
    --location ${AZURE_REGION}

echo -e "${GREEN}✓ Resource Group created${NC}"
echo ""

# Step 2: Create Azure Container Registry
echo -e "${YELLOW}Step 2: Creating Azure Container Registry...${NC}"
az acr create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${ACR_NAME} \
    --sku Standard \
    --admin-enabled true

ACR_LOGIN_SERVER=$(az acr show --name ${ACR_NAME} --resource-group ${RESOURCE_GROUP} --query loginServer --output tsv)
ACR_USERNAME=$(az acr credential show --name ${ACR_NAME} --resource-group ${RESOURCE_GROUP} --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name ${ACR_NAME} --resource-group ${RESOURCE_GROUP} --query passwords[0].value --output tsv)

echo -e "${GREEN}✓ ACR created: ${ACR_LOGIN_SERVER}${NC}"
echo ""

# Step 3: Build and Push Docker Image
echo -e "${YELLOW}Step 3: Building and pushing Docker image...${NC}"
cd ../..

az acr build \
    --registry ${ACR_NAME} \
    --image lab4all:latest \
    --file Dockerfile \
    .

echo -e "${GREEN}✓ Docker image pushed to ACR${NC}"
echo ""

# Step 4: Create PostgreSQL Database
echo -e "${YELLOW}Step 4: Creating PostgreSQL Database...${NC}"
az postgres flexible-server create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${DB_SERVER_NAME} \
    --location ${AZURE_REGION} \
    --admin-user postgres \
    --admin-password ${DB_PASSWORD} \
    --sku-name Standard_B2s \
    --tier Burstable \
    --version 15 \
    --storage-size 128 \
    --public-access 0.0.0.0-255.255.255.255 \
    --backup-retention 7

# Create database
az postgres flexible-server db create \
    --resource-group ${RESOURCE_GROUP} \
    --server-name ${DB_SERVER_NAME} \
    --database-name jal_sarovar_prod

DB_HOST="${DB_SERVER_NAME}.postgres.database.azure.com"

echo -e "${GREEN}✓ PostgreSQL Database created${NC}"
echo ""

# Step 5: Create Storage Account for uploads
echo -e "${YELLOW}Step 5: Creating Storage Account...${NC}"
STORAGE_ACCOUNT="${ENVIRONMENT}lab4allstorage"

az storage account create \
    --name ${STORAGE_ACCOUNT} \
    --resource-group ${RESOURCE_GROUP} \
    --location ${AZURE_REGION} \
    --sku Standard_LRS \
    --kind StorageV2

STORAGE_KEY=$(az storage account keys list --account-name ${STORAGE_ACCOUNT} --resource-group ${RESOURCE_GROUP} --query [0].value --output tsv)

# Create containers
az storage container create --name uploads --account-name ${STORAGE_ACCOUNT} --account-key ${STORAGE_KEY}
az storage container create --name models --account-name ${STORAGE_ACCOUNT} --account-key ${STORAGE_KEY}

echo -e "${GREEN}✓ Storage Account created${NC}"
echo ""

# Step 6: Deploy Container Instance
echo -e "${YELLOW}Step 6: Deploying Container Instance...${NC}"
az container create \
    --resource-group ${RESOURCE_GROUP} \
    --name ${APP_NAME} \
    --image ${ACR_LOGIN_SERVER}/lab4all:latest \
    --cpu 2 \
    --memory 4 \
    --registry-login-server ${ACR_LOGIN_SERVER} \
    --registry-username ${ACR_USERNAME} \
    --registry-password ${ACR_PASSWORD} \
    --dns-name-label ${APP_NAME} \
    --ports 8000 \
    --environment-variables \
        FLASK_ENV=production \
        DB_HOST=${DB_HOST} \
        DB_PORT=5432 \
        DB_NAME=jal_sarovar_prod \
        DB_USER=postgres \
        DB_PASSWORD=${DB_PASSWORD} \
        SECRET_KEY=${SECRET_KEY} \
        AZURE_STORAGE_ACCOUNT=${STORAGE_ACCOUNT} \
        AZURE_STORAGE_KEY=${STORAGE_KEY}

FQDN=$(az container show --resource-group ${RESOURCE_GROUP} --name ${APP_NAME} --query ipAddress.fqdn --output tsv)

echo -e "${GREEN}✓ Container Instance deployed${NC}"
echo ""

# Step 7: Run Database Migrations
echo -e "${YELLOW}Step 7: Running database migrations...${NC}"
az container exec \
    --resource-group ${RESOURCE_GROUP} \
    --name ${APP_NAME} \
    --exec-command "flask db upgrade"

echo -e "${GREEN}✓ Database migrations completed${NC}"
echo ""

# Step 8: Deployment Summary
echo -e "${YELLOW}Deployment Summary${NC}"
echo "=========================================="
echo -e "${GREEN}Application URL:${NC} http://${FQDN}:8000"
echo -e "${GREEN}Database Host:${NC} ${DB_HOST}"
echo -e "${GREEN}Storage Account:${NC} ${STORAGE_ACCOUNT}"
echo -e "${GREEN}Container Registry:${NC} ${ACR_LOGIN_SERVER}"
echo ""

echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure Application Gateway for SSL termination"
echo "2. Set up Azure Monitor for logging and alerts"
echo "3. Configure automated backups"
echo "4. Review network security groups"
echo "5. Set up Azure Front Door for CDN and WAF"
echo ""
echo "To view logs:"
echo "  az container logs --resource-group ${RESOURCE_GROUP} --name ${APP_NAME} --follow"
echo ""
echo "To update the application:"
echo "  ./deploy.sh ${ENVIRONMENT}"
