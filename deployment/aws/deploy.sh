#!/bin/bash
# ============================================================================
# Lab4All Web Application - AWS Deployment Script
# Deploys the application to AWS using CloudFormation and ECS
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-production}"
AWS_REGION="${AWS_REGION:-ap-south-1}"
STACK_NAME="${ENVIRONMENT}-lab4all-stack"
ECR_REPO_NAME="lab4all"

echo -e "${GREEN}Lab4All AWS Deployment Script${NC}"
echo "Environment: ${ENVIRONMENT}"
echo "AWS Region: ${AWS_REGION}"
echo "Stack Name: ${STACK_NAME}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed${NC}"
    echo "Install it from: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed${NC}"
    echo "Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites check passed${NC}"
echo ""

# Prompt for sensitive parameters
read -sp "Enter database master password (min 8 characters): " DB_PASSWORD
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

# Step 1: Create ECR Repository
echo -e "${YELLOW}Step 1: Creating ECR Repository...${NC}"
aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} &> /dev/null || \
aws ecr create-repository \
    --repository-name ${ECR_REPO_NAME} \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256

ECR_URI=$(aws ecr describe-repositories --repository-names ${ECR_REPO_NAME} --region ${AWS_REGION} --query 'repositories[0].repositoryUri' --output text)
echo -e "${GREEN}✓ ECR Repository: ${ECR_URI}${NC}"
echo ""

# Step 2: Build and Push Docker Image
echo -e "${YELLOW}Step 2: Building Docker image...${NC}"
cd ../..
docker build -t ${ECR_REPO_NAME}:latest .

echo -e "${YELLOW}Pushing to ECR...${NC}"
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}
docker tag ${ECR_REPO_NAME}:latest ${ECR_URI}:latest
docker push ${ECR_URI}:latest

echo -e "${GREEN}✓ Docker image pushed to ECR${NC}"
echo ""

# Step 3: Deploy CloudFormation Stack
echo -e "${YELLOW}Step 3: Deploying CloudFormation stack...${NC}"
cd deployment/aws

aws cloudformation deploy \
    --template-file cloudformation-template.yaml \
    --stack-name ${STACK_NAME} \
    --region ${AWS_REGION} \
    --parameter-overrides \
        EnvironmentName=${ENVIRONMENT} \
        DBPassword=${DB_PASSWORD} \
        SecretKey=${SECRET_KEY} \
    --capabilities CAPABILITY_IAM \
    --no-fail-on-empty-changeset

echo -e "${GREEN}✓ CloudFormation stack deployed${NC}"
echo ""

# Step 4: Run Database Migrations
echo -e "${YELLOW}Step 4: Running database migrations...${NC}"

# Get ECS cluster and service names
CLUSTER_NAME=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query "Stacks[0].Outputs[?ExportName=='${ENVIRONMENT}-ecs-cluster'].OutputValue" --output text)

# Get a running task ARN
TASK_ARN=$(aws ecs list-tasks --cluster ${CLUSTER_NAME} --region ${AWS_REGION} --query 'taskArns[0]' --output text)

if [ "${TASK_ARN}" != "None" ] && [ -n "${TASK_ARN}" ]; then
    echo "Running migrations on task: ${TASK_ARN}"
    aws ecs execute-command \
        --cluster ${CLUSTER_NAME} \
        --task ${TASK_ARN} \
        --container lab4all-web \
        --region ${AWS_REGION} \
        --interactive \
        --command "flask db upgrade"
else
    echo -e "${YELLOW}⚠ No running tasks found. Please run migrations manually after tasks start.${NC}"
fi

echo ""

# Step 5: Get Outputs
echo -e "${YELLOW}Step 5: Deployment Summary${NC}"
echo "=========================================="

ALB_URL=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query "Stacks[0].Outputs[?ExportName=='${ENVIRONMENT}-alb-url'].OutputValue" --output text)
DB_ENDPOINT=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query "Stacks[0].Outputs[?ExportName=='${ENVIRONMENT}-db-endpoint'].OutputValue" --output text)
S3_BUCKET=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${AWS_REGION} --query "Stacks[0].Outputs[?ExportName=='${ENVIRONMENT}-s3-bucket'].OutputValue" --output text)

echo -e "${GREEN}Application URL:${NC} http://${ALB_URL}"
echo -e "${GREEN}Database Endpoint:${NC} ${DB_ENDPOINT}"
echo -e "${GREEN}S3 Bucket:${NC} ${S3_BUCKET}"
echo -e "${GREEN}ECS Cluster:${NC} ${CLUSTER_NAME}"
echo ""

echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Configure a custom domain and SSL certificate"
echo "2. Set up CloudWatch alarms and monitoring"
echo "3. Configure automated backups"
echo "4. Review security group rules"
echo "5. Enable WAF for additional security"
echo ""
echo "To view logs:"
echo "  aws logs tail /ecs/${ENVIRONMENT}/lab4all --follow --region ${AWS_REGION}"
echo ""
echo "To update the application:"
echo "  ./deploy.sh ${ENVIRONMENT}"
