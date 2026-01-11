# Jal Sarovar Deployment Files

This directory contains all deployment configurations and scripts for the Jal Sarovar Water Quality Management System.

## 🚀 Quick Start - Deploy to demo.jalsarovar.com

**Recommended Method**: SCP + Tar (Simplest and Fastest)

```bash
# Step 1: Create deployment package (On your Mac)
cd /Users/test/lab4all_wflow_RELEASE_RONALD/jalsarovar
./deployment/scripts/create_deployment_package.sh

# Step 2: Transfer to server
scp jalsarovar_*.tar.gz user@demo.jalsarovar.com:/tmp/

# Step 3: Deploy on server
ssh user@demo.jalsarovar.com
cd /tmp && tar -xzf jalsarovar_*.tar.gz && cd jalsarovar_*
sudo bash deployment/scripts/remote_setup.sh
```

**See**: [DEPLOY_TO_DEMO.md](../DEPLOY_TO_DEMO.md) for complete guide.

---

## Alternative Deployment Methods

### Option 1: Docker Compose (For Testing)

```bash
# From root directory
cp .env.production.template .env.production
nano .env.production  # Configure settings
docker-compose up -d
```

### Option 2: AWS ECS

```bash
cd deployment/aws
./deploy.sh production
```

### Option 3: Azure Container Instances

```bash
cd deployment/azure
./deploy.sh production
```

### Option 4: Google Cloud Run

```bash
cd deployment/gcp
./deploy.sh production
```

## Directory Structure

```
deployment/
├── aws/
│   ├── cloudformation-template.yaml   # AWS infrastructure as code
│   └── deploy.sh                      # AWS deployment script
├── azure/
│   └── deploy.sh                      # Azure deployment script
├── gcp/
│   └── deploy.sh                      # GCP deployment script
├── systemd/
│   └── lab4all.service                # Systemd service unit
├── scripts/
│   ├── create_deployment_package.sh   # Create tar.gz for deployment
│   ├── remote_setup.sh                # Automated server setup
│   └── backup.sh                      # Database backup script
└── README.md                          # This file
```

## Files in Root Directory

```
jalsarovar/
├── Dockerfile                         # Docker image definition
├── docker-compose.yml                 # Multi-container orchestration
├── .dockerignore                      # Docker build exclusions
├── gunicorn_config.py                 # WSGI server configuration
├── .env.production.template           # Environment template
├── nginx/                             # Nginx configurations
│   ├── nginx.conf                     # Main nginx config
│   ├── conf.d/
│   │   └── lab4all.conf              # Site-specific config
│   └── ssl/
│       └── README.md                  # SSL certificate guide
├── DEPLOYMENT.md                      # Complete deployment guide
└── DEPLOY_TO_DEMO.md                  # Quick guide for demo.jalsarovar.com
```

## Prerequisites

- Docker & Docker Compose (for containerized deployments)
- AWS/Azure/GCP CLI (for cloud deployments)
- PostgreSQL 15 (for traditional deployments)
- Nginx (for traditional deployments)
- Python 3.11 (for traditional deployments)

## Configuration Checklist

Before deploying, ensure you have:

- [ ] Copied `.env.production.template` to `.env.production`
- [ ] Set strong `SECRET_KEY` (32+ characters)
- [ ] Configured database credentials
- [ ] Set up SSL certificates (production)
- [ ] Configured email settings (optional)
- [ ] Reviewed security settings

## Quick Commands

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web flask db upgrade

# Create admin user
docker-compose exec web flask create-admin

# Backup database
docker-compose run --rm backup

# Stop services
docker-compose down
```

### Cloud Deployments

```bash
# AWS
cd deployment/aws && ./deploy.sh production

# Azure
cd deployment/azure && ./deploy.sh production

# GCP
cd deployment/gcp && ./deploy.sh production
```

### Traditional Server (demo.jalsarovar.com)

```bash
# Check service status
sudo systemctl status jalsarovar

# View logs
sudo journalctl -u jalsarovar -f

# Restart service
sudo systemctl restart jalsarovar
```

## Environment Variables

Key environment variables to configure:

```ini
# Flask
FLASK_ENV=production
SECRET_KEY=<your-secret-key>

# Database
DB_HOST=<database-host>
DB_PORT=5432
DB_NAME=jal_sarovar_prod
DB_USER=<database-user>
DB_PASSWORD=<database-password>

# Application
PORT=8000
WORKERS=4
LOG_LEVEL=info
```

See `.env.production.template` for complete list.

## Security Notes

1. **Never commit `.env.production` to version control**
2. Use strong, unique passwords (16+ characters)
3. Enable SSL/TLS in production
4. Configure firewall rules appropriately
5. Keep dependencies updated
6. Enable automated backups
7. Set up monitoring and alerting

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "jal-sarovar"
}
```

### View Logs

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
az container logs --resource-group production-lab4all-rg --name production-lab4all --follow
```

**GCP**:
```bash
gcloud run services logs read production-lab4all --region=asia-south1
```

## Backup and Recovery

### Create Backup

```bash
# Docker
docker-compose run --rm backup

# Manual (any environment)
cd deployment/scripts
./backup.sh
```

### Restore Backup

```bash
gunzip -c /backups/lab4all_backup_YYYYMMDD_HHMMSS.sql.gz | \
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME
```

## Scaling

### Horizontal Scaling

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

**GCP** (automatic based on traffic):
```bash
gcloud run deploy production-lab4all \
    --min-instances=2 \
    --max-instances=100
```

## Troubleshooting

### Application won't start

1. Check logs (see Monitoring section)
2. Verify database connection
3. Check environment variables
4. Ensure all dependencies are installed

### Database connection errors

```bash
# Test connection
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1"
```

### 502 Bad Gateway

1. Check if application is running: `curl http://localhost:8000/health`
2. Test nginx configuration: `sudo nginx -t`
3. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`

## Cost Estimates (Monthly)

| Platform | Configuration | Estimated Cost |
|----------|--------------|----------------|
| **AWS ECS** | 2 tasks, RDS Multi-AZ, ALB | ~$230 USD |
| **Azure** | Container Instances, PostgreSQL Flexible | ~$160 USD |
| **GCP** | Cloud Run, Cloud SQL | ~$105 USD |
| **Self-hosted** | VPS (4 vCPU, 8GB RAM) | ~$40-80 USD |

*Costs vary based on region, usage, and data transfer*

## Support

For detailed deployment instructions, see [DEPLOYMENT.md](../DEPLOYMENT.md)

For issues:
1. Check logs
2. Review documentation
3. Open GitHub issue
4. Contact support team

## License

See main repository LICENSE file.

---

**Quick Links**:
- [Complete Deployment Guide](../DEPLOYMENT.md)
- [Docker Compose Configuration](../docker-compose.yml)
- [Environment Template](../.env.production.template)
- [Nginx Configuration](../nginx/)
- [AWS CloudFormation Template](aws/cloudformation-template.yaml)
