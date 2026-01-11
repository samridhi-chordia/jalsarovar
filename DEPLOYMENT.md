# Lab4All Web Application - Cloud Deployment Guide

Complete guide for deploying the Jal Sarovar Water Quality Management System to cloud platforms.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Deployment Options](#deployment-options)
5. [Docker Deployment](#docker-deployment)
6. [AWS Deployment](#aws-deployment)
7. [Azure Deployment](#azure-deployment)
8. [Google Cloud Platform Deployment](#gcp-deployment)
9. [Traditional Server Deployment](#traditional-server-deployment)
10. [Post-Deployment Configuration](#post-deployment-configuration)
11. [Security Hardening](#security-hardening)
12. [Monitoring and Logging](#monitoring-and-logging)
13. [Backup and Recovery](#backup-and-recovery)
14. [Scaling](#scaling)
15. [Troubleshooting](#troubleshooting)

---

## Overview

The Lab4All Web Application is a Flask-based water quality management system designed for deployment on cloud infrastructure. This guide covers multiple deployment scenarios from simple Docker containers to fully managed cloud services.

### Architecture Components

- **Web Application**: Flask + Gunicorn (Python 3.11)
- **Database**: PostgreSQL 15
- **Reverse Proxy**: Nginx
- **Cache** (Optional): Redis
- **Storage**: Local filesystem or cloud object storage (S3/Azure Blob/GCS)
- **ML Models**: Stored in persistent volumes or cloud storage

---

## Prerequisites

### Required Tools

```bash
# Docker
docker --version  # >= 20.10

# Docker Compose
docker-compose --version  # >= 2.0

# Cloud CLI (choose your platform)
aws --version      # AWS CLI >= 2.0
az --version       # Azure CLI >= 2.0
gcloud --version   # Google Cloud SDK >= 400.0

# Git
git --version  # >= 2.0
```

### Required Access

- [ ] Cloud platform account (AWS/Azure/GCP)
- [ ] Domain name (optional but recommended)
- [ ] SSL certificate (Let's Encrypt or purchased)
- [ ] Access to SMTP server (for email notifications)

### System Requirements

#### Minimum Production Requirements

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 100 GB SSD
- **Network**: 100 Mbps

#### Recommended Production Requirements

- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 500 GB SSD (with auto-scaling)
- **Network**: 1 Gbps
- **Load Balancer**: Yes
- **Database**: Managed service with automated backups

---

## Pre-Deployment Checklist

### 1. Configuration

- [ ] Copy `.env.production.template` to `.env.production`
- [ ] Generate strong SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set database credentials (minimum 16 characters)
- [ ] Configure email settings (if using notifications)
- [ ] Update domain name in nginx configuration
- [ ] Obtain SSL certificates

### 2. Database

- [ ] Create PostgreSQL 15 database
- [ ] Set up database user with appropriate permissions
- [ ] Configure database backups
- [ ] Test database connectivity

### 3. Storage

- [ ] Create uploads directory or configure cloud storage
- [ ] Create ML models directory
- [ ] Set appropriate permissions

### 4. Security

- [ ] Review security group/firewall rules
- [ ] Enable SSL/TLS
- [ ] Configure rate limiting
- [ ] Set up Web Application Firewall (WAF)
- [ ] Enable DDoS protection

### 5. Monitoring

- [ ] Set up logging aggregation
- [ ] Configure performance monitoring
- [ ] Create dashboards
- [ ] Set up alerting

---

## Deployment Options

### Comparison Matrix

| Feature | Docker Compose | AWS ECS | Azure Container Instances | GCP Cloud Run | Traditional Server |
|---------|---------------|---------|---------------------------|---------------|-------------------|
| **Setup Complexity** | Low | Medium | Low | Low | High |
| **Cost** | Server cost only | Pay per hour | Pay per second | Pay per request | Server cost + maintenance |
| **Scalability** | Manual | Auto (horizontal) | Manual | Auto (serverless) | Manual |
| **Managed Database** | No | RDS (managed) | Yes | Cloud SQL (managed) | No |
| **Maintenance** | You manage | AWS manages infra | Azure manages infra | Google manages infra | You manage all |
| **Best For** | Development, small deployments | Production, predictable traffic | Development, testing | Production, variable traffic | Full control needed |

---

## Docker Deployment

Best for: Development, testing, small production deployments

### Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd lab4all_webapp

# 2. Create environment file
cp .env.production.template .env.production
nano .env.production  # Fill in required values

# 3. Generate SSL certificates (for development)
cd nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout private.key \
    -out certificate.crt \
    -subj "/C=IN/ST=Delhi/L=Delhi/O=Lab4All/CN=localhost"
cd ../..

# 4. Start services
docker-compose up -d

# 5. Run database migrations
docker-compose exec web flask db upgrade

# 6. Create admin user (optional)
docker-compose exec web flask create-admin

# 7. Check status
docker-compose ps
docker-compose logs -f web
```

### Access Application

- **HTTP**: http://localhost
- **HTTPS**: https://localhost
- **Direct**: http://localhost:8000

### Management Commands

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Database backup
docker-compose run --rm backup

# Access web container
docker-compose exec web bash

# Run migrations
docker-compose exec web flask db upgrade

# Scale web instances
docker-compose up -d --scale web=3
```

### Production Considerations

1. **Use Let's Encrypt for SSL**:
```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

2. **Configure Production Environment**:
   - Set strong passwords
   - Enable SSL/TLS
   - Configure backups
   - Set up monitoring

3. **Persistent Data**:
   - PostgreSQL data: `postgres_data` volume
   - Uploads: `./uploads` bind mount
   - ML models: `ml_models` volume

---

## AWS Deployment

Best for: Production deployments with AWS ecosystem integration

### Architecture

- **Compute**: ECS Fargate
- **Database**: RDS PostgreSQL (Multi-AZ)
- **Load Balancer**: Application Load Balancer
- **Storage**: S3
- **Registry**: ECR
- **Networking**: VPC with public and private subnets

### Deployment Steps

```bash
# 1. Install AWS CLI
pip install awscli
aws configure

# 2. Set environment variables
export AWS_REGION=ap-south-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 3. Run deployment script
cd deployment/aws
chmod +x deploy.sh
./deploy.sh production

# Follow prompts for:
# - Database password (min 8 characters)
# - Flask secret key (min 32 characters)
```

### What the Script Does

1. Creates ECR repository
2. Builds and pushes Docker image
3. Creates CloudFormation stack:
   - VPC with 2 public + 2 private subnets
   - Security groups
   - RDS PostgreSQL (Multi-AZ)
   - Application Load Balancer
   - ECS cluster and service
   - S3 bucket for storage
4. Runs database migrations

### Access Application

After deployment completes, the script outputs the ALB URL:

```
Application URL: http://production-lab4all-alb-xxxxxxxxx.ap-south-1.elb.amazonaws.com
```

### Cost Estimate (ap-south-1 region)

| Component | Specification | Monthly Cost (USD) |
|-----------|--------------|-------------------|
| ECS Fargate | 2 tasks (1 vCPU, 2GB RAM) | ~$40 |
| RDS PostgreSQL | db.t3.medium (Multi-AZ) | ~$150 |
| ALB | Standard | ~$20 |
| Data Transfer | 100 GB outbound | ~$10 |
| S3 | 500 GB storage | ~$12 |
| **Total** | | **~$232/month** |

### Post-Deployment Tasks

```bash
# 1. Configure custom domain
# In Route 53, create CNAME record pointing to ALB

# 2. Add SSL certificate
# In ACM (AWS Certificate Manager):
aws acm request-certificate \
    --domain-name lab4all.example.com \
    --validation-method DNS

# 3. Update ALB listener to HTTPS
aws elbv2 create-listener \
    --load-balancer-arn <ALB-ARN> \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=<CERT-ARN> \
    --default-actions Type=forward,TargetGroupArn=<TG-ARN>

# 4. View logs
aws logs tail /ecs/production/lab4all --follow

# 5. Scale service
aws ecs update-service \
    --cluster production-lab4all-cluster \
    --service production-lab4all-service \
    --desired-count 4
```

### Cleanup

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name production-lab4all-stack

# Delete ECR images
aws ecr batch-delete-image \
    --repository-name lab4all \
    --image-ids imageTag=latest

# Empty and delete S3 bucket
aws s3 rm s3://production-lab4all-storage-${AWS_ACCOUNT_ID} --recursive
aws s3 rb s3://production-lab4all-storage-${AWS_ACCOUNT_ID}
```

---

## Azure Deployment

Best for: Organizations using Microsoft Azure ecosystem

### Architecture

- **Compute**: Azure Container Instances
- **Database**: Azure Database for PostgreSQL Flexible Server
- **Storage**: Azure Blob Storage
- **Registry**: Azure Container Registry
- **Networking**: Virtual Network

### Deployment Steps

```bash
# 1. Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
az login

# 2. Set environment variables
export AZURE_REGION=centralindia

# 3. Run deployment script
cd deployment/azure
chmod +x deploy.sh
./deploy.sh production

# Follow prompts for credentials
```

### Access Application

```
Application URL: http://production-lab4all.centralindia.azurecontainer.io:8000
```

### Cost Estimate (Central India region)

| Component | Specification | Monthly Cost (USD) |
|-----------|--------------|-------------------|
| Container Instances | 2 vCPU, 4 GB RAM | ~$70 |
| PostgreSQL Flexible | Standard_B2s | ~$60 |
| Blob Storage | 500 GB | ~$10 |
| Container Registry | Standard | ~$20 |
| **Total** | | **~$160/month** |

### Post-Deployment Tasks

```bash
# View logs
az container logs --resource-group production-lab4all-rg \
    --name production-lab4all --follow

# Configure Application Gateway for SSL
az network application-gateway create \
    --name lab4all-gateway \
    --resource-group production-lab4all-rg \
    --location centralindia

# Scale instances
az container create \
    --resource-group production-lab4all-rg \
    --name production-lab4all-2 \
    # ... (copy configuration from deploy script)
```

---

## GCP Deployment

Best for: Serverless deployments with automatic scaling

### Architecture

- **Compute**: Cloud Run (serverless containers)
- **Database**: Cloud SQL PostgreSQL
- **Storage**: Cloud Storage
- **Registry**: Container Registry
- **Networking**: VPC

### Deployment Steps

```bash
# 1. Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
gcloud init

# 2. Set project ID
export GCP_PROJECT=your-project-id
export GCP_REGION=asia-south1

# 3. Run deployment script
cd deployment/gcp
chmod +x deploy.sh
./deploy.sh production

# Follow prompts for credentials
```

### Access Application

```
Application URL: https://production-lab4all-xxxxxxxxx-an.a.run.app
```

### Cost Estimate (Mumbai region)

| Component | Specification | Monthly Cost (USD) |
|-----------|--------------|-------------------|
| Cloud Run | 1M requests, 2 vCPU, 2GB RAM | ~$50 |
| Cloud SQL | db-g1-small | ~$40 |
| Cloud Storage | 500 GB | ~$10 |
| Container Registry | Standard | ~$5 |
| **Total** | | **~$105/month** |

**Note**: Cloud Run pricing is pay-per-request, making it very cost-effective for variable traffic.

### Post-Deployment Tasks

```bash
# Map custom domain
gcloud run services add-iam-policy-binding production-lab4all \
    --region=asia-south1 \
    --member=allUsers \
    --role=roles/run.invoker

gcloud run domain-mappings create \
    --service production-lab4all \
    --domain lab4all.example.com \
    --region=asia-south1

# View logs
gcloud run services logs read production-lab4all \
    --region=asia-south1 --limit=50

# Update deployment
gcloud run deploy production-lab4all \
    --image gcr.io/${GCP_PROJECT}/production-lab4all \
    --region asia-south1
```

---

## Traditional Server Deployment

Best for: On-premise deployments or full control requirements

### Server Requirements

- **OS**: Ubuntu 22.04 LTS (recommended)
- **Python**: 3.11
- **PostgreSQL**: 15
- **Nginx**: Latest stable
- **Systemd**: For service management

### Deployment Steps

```bash
# 1. Update system
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install dependencies
sudo apt-get install -y \
    python3.11 python3.11-venv python3-pip \
    postgresql-15 postgresql-contrib \
    nginx \
    git curl

# 3. Create application user
sudo useradd -m -s /bin/bash lab4all
sudo mkdir -p /opt/lab4all
sudo chown lab4all:lab4all /opt/lab4all

# 4. Clone repository
sudo -u lab4all git clone <repository-url> /opt/lab4all/lab4all_webapp

# 5. Set up Python virtual environment
sudo -u lab4all python3.11 -m venv /opt/lab4all/venv
sudo -u lab4all /opt/lab4all/venv/bin/pip install --upgrade pip
sudo -u lab4all /opt/lab4all/venv/bin/pip install -r /opt/lab4all/lab4all_webapp/requirements.txt

# 6. Configure PostgreSQL
sudo -u postgres createuser lab4all
sudo -u postgres createdb -O lab4all jal_sarovar_prod
sudo -u postgres psql -c "ALTER USER lab4all WITH PASSWORD 'secure-password-here';"

# 7. Configure environment
sudo -u lab4all cp /opt/lab4all/lab4all_webapp/.env.production.template \
    /opt/lab4all/lab4all_webapp/.env.production
sudo -u lab4all nano /opt/lab4all/lab4all_webapp/.env.production

# 8. Run migrations
cd /opt/lab4all/lab4all_webapp
sudo -u lab4all /opt/lab4all/venv/bin/flask db upgrade

# 9. Install systemd service
sudo cp deployment/systemd/lab4all.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable lab4all
sudo systemctl start lab4all

# 10. Configure Nginx
sudo cp nginx/conf.d/lab4all.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/lab4all.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 11. Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 12. Set up SSL with Let's Encrypt
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d lab4all.example.com
```

### Service Management

```bash
# Check status
sudo systemctl status lab4all

# View logs
sudo journalctl -u lab4all -f

# Restart service
sudo systemctl restart lab4all

# Stop service
sudo systemctl stop lab4all
```

---

## Post-Deployment Configuration

### 1. Create Admin User

```bash
# Docker
docker-compose exec web python3 -c "
from app import create_app, db
from app.models import User
app = create_app('production')
with app.app_context():
    admin = User(
        username='admin',
        email='admin@example.com',
        is_admin=True
    )
    admin.set_password('secure-admin-password')
    db.session.add(admin)
    db.session.commit()
    print('Admin user created')
"

# AWS/Azure/GCP - adapt the container exec command
```

### 2. Upload ML Models

```bash
# Upload pre-trained models to appropriate location
# - Docker: /app/ALL_MODELS volume
# - AWS: S3 bucket
# - Azure: Blob storage
# - GCP: Cloud Storage
```

### 3. Configure Email

Update `.env.production`:

```ini
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@lab4all.example.com
```

### 4. Set Up Monitoring

See [Monitoring and Logging](#monitoring-and-logging) section.

---

## Security Hardening

### 1. Database Security

```sql
-- Restrict database user permissions
REVOKE ALL ON DATABASE jal_sarovar_prod FROM PUBLIC;
GRANT CONNECT ON DATABASE jal_sarovar_prod TO lab4all;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lab4all;

-- Enable SSL connections
ALTER SYSTEM SET ssl = on;

-- Require SSL for user
ALTER USER lab4all SET ssl_mode = 'require';
```

### 2. Application Security

```ini
# .env.production
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=3600

# Enable rate limiting
RATELIMIT_ENABLED=True
RATELIMIT_DEFAULT=200 per day, 50 per hour
```

### 3. Nginx Security Headers

Already configured in `nginx/conf.d/lab4all.conf`:

- Strict-Transport-Security (HSTS)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Content-Security-Policy

### 4. Network Security

**AWS**:
```bash
# Restrict RDS access to ECS security group only
# Configure in CloudFormation template (already done)
```

**Firewall Rules**:
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp  # Database should not be publicly accessible
```

### 5. Regular Updates

```bash
# Set up automatic security updates (Ubuntu)
sudo apt-get install unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Monitoring and Logging

### Application Logs

**Docker**:
```bash
docker-compose logs -f web
```

**Systemd**:
```bash
sudo journalctl -u lab4all -f
```

**AWS**:
```bash
aws logs tail /ecs/production/lab4all --follow
```

**Azure**:
```bash
az container logs --resource-group production-lab4all-rg \
    --name production-lab4all --follow
```

**GCP**:
```bash
gcloud run services logs read production-lab4all \
    --region=asia-south1 --limit=50
```

### Performance Monitoring

**Recommended Tools**:

1. **Application Performance**:
   - New Relic
   - Datadog
   - AWS CloudWatch (for AWS deployments)
   - Azure Monitor (for Azure deployments)
   - Google Cloud Monitoring (for GCP deployments)

2. **Database Monitoring**:
   - pgAdmin
   - Datadog PostgreSQL integration
   - AWS RDS Performance Insights
   - Azure Database monitoring

3. **Infrastructure Monitoring**:
   - Prometheus + Grafana
   - Netdata
   - Cloud-native monitoring (CloudWatch/Azure Monitor/Stackdriver)

### Setting Up Prometheus + Grafana

```yaml
# Add to docker-compose.yml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## Backup and Recovery

### Automated Backups

**Docker**:
```bash
# Add to crontab
0 2 * * * docker-compose run --rm backup
```

**AWS RDS**:
- Automated backups enabled in CloudFormation (7-day retention)
- Manual snapshots via AWS Console

**Azure**:
```bash
# Automated backups (7 days)
az postgres flexible-server backup create \
    --resource-group production-lab4all-rg \
    --name production-lab4all-db \
    --backup-name manual-backup-$(date +%Y%m%d)
```

**GCP**:
```bash
# Automated via Cloud Scheduler (configured in deploy script)
gcloud sql backups create \
    --instance=production-lab4all-db
```

### Manual Backup

```bash
# Run backup script
cd deployment/scripts
chmod +x backup.sh
./backup.sh

# Backup file created at: /backups/lab4all_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Restore from Backup

```bash
# Extract and restore
gunzip -c /backups/lab4all_backup_20250101_020000.sql.gz | \
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

### Disaster Recovery Plan

1. **Regular backups**: Daily automated + weekly manual
2. **Off-site storage**: Upload backups to S3/Azure Blob/GCS
3. **Testing**: Quarterly restore tests
4. **Documentation**: Keep recovery procedures updated
5. **RTO/RPO**:
   - Recovery Time Objective (RTO): < 4 hours
   - Recovery Point Objective (RPO): < 24 hours

---

## Scaling

### Vertical Scaling (Scale Up)

**Docker**:
Update `docker-compose.yml`:
```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

**AWS**:
Update task definition CPU/Memory in CloudFormation template.

**Azure**:
```bash
az container create \
    --cpu 4 \
    --memory 8
```

**GCP**:
```bash
gcloud run deploy production-lab4all \
    --cpu=4 \
    --memory=8Gi
```

### Horizontal Scaling (Scale Out)

**Docker**:
```bash
docker-compose up -d --scale web=4
```

**AWS**:
```bash
aws ecs update-service \
    --cluster production-lab4all-cluster \
    --service production-lab4all-service \
    --desired-count 10
```

**GCP Cloud Run**:
Automatic scaling based on traffic (0 to 100 instances by default).

### Database Scaling

**Read Replicas**:

AWS RDS:
```bash
aws rds create-db-instance-read-replica \
    --db-instance-identifier lab4all-read-replica \
    --source-db-instance-identifier production-lab4all-db
```

**Connection Pooling**:
Already configured in `config.py`:
```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20
}
```

---

## Troubleshooting

### Common Issues

#### 1. Application won't start

**Check logs**:
```bash
# Docker
docker-compose logs web

# Systemd
sudo journalctl -u lab4all -n 50

# Cloud platforms - see Monitoring section
```

**Common causes**:
- Database connection failure
- Missing environment variables
- Permission issues

#### 2. Database connection errors

**Test connection**:
```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"
```

**Check**:
- Database is running
- Firewall allows connection
- Credentials are correct
- SSL settings match

#### 3. 502 Bad Gateway (Nginx)

**Check**:
- Application is running: `curl http://localhost:8000/health`
- Nginx configuration: `sudo nginx -t`
- Logs: `sudo tail -f /var/log/nginx/error.log`

#### 4. High memory usage

**Check**:
```bash
# Container stats
docker stats

# System memory
free -h

# Process memory
ps aux --sort=-%mem | head
```

**Solutions**:
- Reduce worker count
- Increase server memory
- Check for memory leaks
- Enable database connection pooling

#### 5. Slow performance

**Check**:
- Database queries: Enable slow query log
- Application logs: Look for slow requests
- Server resources: CPU, memory, disk I/O
- Network latency

**Optimize**:
- Add database indexes
- Enable caching (Redis)
- Use CDN for static files
- Optimize queries

---

## Support

For issues and questions:

1. Check logs first
2. Review this documentation
3. Check application issues on GitHub
4. Contact support team

---

## Appendix

### Environment Variables Reference

See `.env.production.template` for complete list.

### Port Reference

- `80`: HTTP (Nginx)
- `443`: HTTPS (Nginx)
- `8000`: Application (Gunicorn)
- `5432`: PostgreSQL
- `6379`: Redis (if used)

### File Locations

- **Application**: `/opt/lab4all/lab4all_webapp` (traditional) or `/app` (Docker)
- **Logs**: `/var/log/lab4all` or `/app/logs`
- **Uploads**: `/app/uploads`
- **ML Models**: `/app/ALL_MODELS` or `/app/models`
- **Backups**: `/backups`

### Health Check Endpoint

```bash
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "service": "jal-sarovar"
}
```

---

**Document Version**: 1.0
**Last Updated**: December 22, 2025
**Maintained By**: Lab4All Development Team
