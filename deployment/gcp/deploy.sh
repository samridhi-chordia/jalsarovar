#!/bin/bash
# ============================================================================
# Lab4All Web Application - Google Cloud Platform Deployment Script
# Deploys the application to GCP using Cloud Run and Cloud SQL
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-production}"
GCP_PROJECT="${GCP_PROJECT:-your-project-id}"
GCP_REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="${ENVIRONMENT}-lab4all"
DB_INSTANCE_NAME="${ENVIRONMENT}-lab4all-db"
BUCKET_NAME="${GCP_PROJECT}-${ENVIRONMENT}-lab4all-storage"

echo -e "${GREEN}Lab4All GCP Deployment Script${NC}"
echo "Environment: ${ENVIRONMENT}"
echo "GCP Project: ${GCP_PROJECT}"
echo "GCP Region: ${GCP_REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: Google Cloud SDK is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    echo "Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check GCP authentication
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo -e "${RED}ERROR: Not authenticated with GCP${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Set project
gcloud config set project ${GCP_PROJECT}

# Prompt for sensitive parameters
read -sp "Enter database password (min 8 characters): " DB_PASSWORD
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

# Step 1: Enable Required APIs
echo -e "${YELLOW}Step 1: Enabling required GCP APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    storage-api.googleapis.com \
    storage-component.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Step 2: Create Cloud SQL Instance
echo -e "${YELLOW}Step 2: Creating Cloud SQL PostgreSQL instance...${NC}"
gcloud sql instances create ${DB_INSTANCE_NAME} \
    --database-version=POSTGRES_15 \
    --tier=db-g1-small \
    --region=${GCP_REGION} \
    --root-password=${DB_PASSWORD} \
    --storage-type=SSD \
    --storage-size=100GB \
    --storage-auto-increase \
    --backup \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=04 \
    --enable-bin-log \
    --database-flags=max_connections=100 \
    || echo "Database instance may already exist"

# Create database
gcloud sql databases create jal_sarovar_prod \
    --instance=${DB_INSTANCE_NAME} \
    || echo "Database may already exist"

# Get connection name
DB_CONNECTION_NAME=$(gcloud sql instances describe ${DB_INSTANCE_NAME} --format="value(connectionName)")

echo -e "${GREEN}✓ Cloud SQL instance created${NC}"
echo "  Connection name: ${DB_CONNECTION_NAME}"
echo ""

# Step 3: Create GCS Bucket
echo -e "${YELLOW}Step 3: Creating Cloud Storage bucket...${NC}"
gsutil mb -l ${GCP_REGION} -c STANDARD gs://${BUCKET_NAME}/ || echo "Bucket may already exist"
gsutil versioning set on gs://${BUCKET_NAME}/

# Create folders
echo "" | gsutil cp - gs://${BUCKET_NAME}/uploads/.gitkeep
echo "" | gsutil cp - gs://${BUCKET_NAME}/models/.gitkeep

echo -e "${GREEN}✓ Cloud Storage bucket created${NC}"
echo ""

# Step 4: Store secrets in Secret Manager
echo -e "${YELLOW}Step 4: Storing secrets in Secret Manager...${NC}"
echo -n ${DB_PASSWORD} | gcloud secrets create db-password --data-file=- --replication-policy=automatic || \
echo -n ${DB_PASSWORD} | gcloud secrets versions add db-password --data-file=-

echo -n ${SECRET_KEY} | gcloud secrets create flask-secret-key --data-file=- --replication-policy=automatic || \
echo -n ${SECRET_KEY} | gcloud secrets versions add flask-secret-key --data-file=-

echo -e "${GREEN}✓ Secrets stored${NC}"
echo ""

# Step 5: Build and Deploy to Cloud Run
echo -e "${YELLOW}Step 5: Building and deploying to Cloud Run...${NC}"
cd ../..

gcloud builds submit --tag gcr.io/${GCP_PROJECT}/${SERVICE_NAME}

gcloud run deploy ${SERVICE_NAME} \
    --image gcr.io/${GCP_PROJECT}/${SERVICE_NAME} \
    --platform managed \
    --region ${GCP_REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --timeout 300 \
    --concurrency 80 \
    --add-cloudsql-instances ${DB_CONNECTION_NAME} \
    --set-env-vars "FLASK_ENV=production,DB_HOST=/cloudsql/${DB_CONNECTION_NAME},DB_PORT=5432,DB_NAME=jal_sarovar_prod,DB_USER=postgres,GCS_BUCKET=${BUCKET_NAME}" \
    --set-secrets "DB_PASSWORD=db-password:latest,SECRET_KEY=flask-secret-key:latest"

SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${GCP_REGION} --format="value(status.url)")

echo -e "${GREEN}✓ Application deployed to Cloud Run${NC}"
echo ""

# Step 6: Run Database Migrations
echo -e "${YELLOW}Step 6: Running database migrations...${NC}"
gcloud run jobs create ${SERVICE_NAME}-migrate \
    --image gcr.io/${GCP_PROJECT}/${SERVICE_NAME} \
    --region ${GCP_REGION} \
    --add-cloudsql-instances ${DB_CONNECTION_NAME} \
    --set-env-vars "FLASK_ENV=production,DB_HOST=/cloudsql/${DB_CONNECTION_NAME},DB_PORT=5432,DB_NAME=jal_sarovar_prod,DB_USER=postgres" \
    --set-secrets "DB_PASSWORD=db-password:latest,SECRET_KEY=flask-secret-key:latest" \
    --command flask \
    --args db,upgrade \
    || echo "Migration job may already exist"

gcloud run jobs execute ${SERVICE_NAME}-migrate --region ${GCP_REGION} --wait

echo -e "${GREEN}✓ Database migrations completed${NC}"
echo ""

# Step 7: Set up Cloud Scheduler for Backups (Optional)
echo -e "${YELLOW}Step 7: Setting up automated backups...${NC}"
gcloud scheduler jobs create http ${SERVICE_NAME}-backup \
    --location ${GCP_REGION} \
    --schedule "0 2 * * *" \
    --uri "https://sqladmin.googleapis.com/sql/v1beta4/projects/${GCP_PROJECT}/instances/${DB_INSTANCE_NAME}/backup" \
    --http-method POST \
    --oauth-service-account-email $(gcloud projects describe ${GCP_PROJECT} --format="value(projectNumber)")@cloudscheduler.iam.gserviceaccount.com \
    || echo "Backup job may already exist"

echo -e "${GREEN}✓ Automated backups configured${NC}"
echo ""

# Step 8: Deployment Summary
echo -e "${YELLOW}Deployment Summary${NC}"
echo "=========================================="
echo -e "${GREEN}Application URL:${NC} ${SERVICE_URL}"
echo -e "${GREEN}Cloud SQL Connection:${NC} ${DB_CONNECTION_NAME}"
echo -e "${GREEN}Storage Bucket:${NC} gs://${BUCKET_NAME}"
echo -e "${GREEN}Container Registry:${NC} gcr.io/${GCP_PROJECT}/${SERVICE_NAME}"
echo ""

echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure a custom domain and SSL certificate"
echo "2. Set up Cloud Monitoring dashboards"
echo "3. Configure Cloud Armor for DDoS protection"
echo "4. Review IAM permissions"
echo "5. Enable VPC Service Controls for additional security"
echo ""
echo "To view logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${GCP_REGION} --limit=50"
echo ""
echo "To update the application:"
echo "  ./deploy.sh ${ENVIRONMENT}"
echo ""
echo "To connect to Cloud SQL:"
echo "  gcloud sql connect ${DB_INSTANCE_NAME} --user=postgres"
