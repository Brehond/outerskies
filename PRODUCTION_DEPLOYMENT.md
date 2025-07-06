# Outer Skies Production Deployment Guide

This guide provides comprehensive instructions for deploying Outer Skies to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [SSL Certificate Setup](#ssl-certificate-setup)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Deployment](#deployment)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Backup Configuration](#backup-configuration)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 20.04+ or CentOS 8+
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: Minimum 20GB (50GB recommended)
- **CPU**: 2+ cores
- **Network**: Public IP with ports 80, 443 open

### Software Requirements

- Docker 20.10+
- Docker Compose 2.0+
- Git
- curl
- PostgreSQL client tools

### Domain & SSL

- Registered domain name
- SSL certificate (Let's Encrypt recommended)

## Server Setup

### 1. Update System

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Install Additional Tools

```bash
# Ubuntu/Debian
sudo apt install -y git curl postgresql-client redis-tools

# CentOS/RHEL
sudo yum install -y git curl postgresql redis
```

## SSL Certificate Setup

### Using Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot

# Get SSL certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Create SSL directory for nginx
sudo mkdir -p /etc/nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /etc/nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /etc/nginx/ssl/key.pem
sudo chmod 600 /etc/nginx/ssl/*.pem

# Set up auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /etc/nginx/ssl/cert.pem && cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /etc/nginx/ssl/key.pem
```

## Environment Configuration

### 1. Clone Repository

```bash
git clone https://github.com/your-username/outer-skies.git
cd outer-skies
```

### 2. Generate Security Keys

```bash
python scripts/generate_security_keys.py
```

### 3. Configure Environment Variables

```bash
# Copy production environment template
cp env.production.example .env.production

# Edit with your actual values
nano .env.production
```

**Required Environment Variables:**

```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
ENVIRONMENT=production

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=outerskies_prod
DB_USER=outerskies_user
DB_PASSWORD=your-secure-database-password
DB_HOST=db
DB_PORT=5432
DATABASE_URL=postgresql://outerskies_user:your-secure-database-password@db:5432/outerskies_prod

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-redis-password
REDIS_URL=redis://:your-secure-redis-password@redis:6379/0

# AI Integration
OPENROUTER_API_KEY=your-openrouter-api-key

# Stripe
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret

# Security
API_KEY=your-api-key
API_SECRET=your-api-secret
ENCRYPTION_KEY=your-encryption-key
ENCRYPTION_SALT=your-encryption-salt

# Monitoring
SENTRY_DSN=https://your-sentry-dsn

# Email (SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

## Database Setup

### 1. Create Database User

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE outerskies_prod;
CREATE USER outerskies_user WITH PASSWORD 'your-secure-database-password';
GRANT ALL PRIVILEGES ON DATABASE outerskies_prod TO outerskies_user;
\q
```

### 2. Test Database Connection

```bash
psql -h localhost -U outerskies_user -d outerskies_prod
```

## Deployment

### 1. Initial Deployment

```bash
# Load environment variables
export $(cat .env.production | xargs)

# Create necessary directories
mkdir -p logs staticfiles media backups ssl

# Copy SSL certificates
sudo cp /etc/nginx/ssl/* ssl/

# Build and start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 2. Using Deployment Script

```bash
# Make script executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh
```

### 3. Verify Deployment

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Test health endpoints
curl -f http://localhost/health/
curl -f http://localhost/api/v1/system/health/
```

## Monitoring & Health Checks

### 1. Health Check Endpoints

- **Basic Health**: `http://yourdomain.com/health/`
- **Detailed Health**: `http://yourdomain.com/api/v1/system/health/`
- **Quick Health**: `http://yourdomain.com/api/v1/system/quick_health/`
- **Performance**: `http://yourdomain.com/api/v1/system/performance/`

### 2. Monitoring Setup

#### Sentry Integration

1. Create Sentry account at https://sentry.io
2. Create new project for Outer Skies
3. Add DSN to environment variables
4. Monitor errors and performance

#### Prometheus & Grafana

```bash
# Add to docker-compose.prod.yml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=your-grafana-password
    ports:
      - "3000:3000"
```

### 3. Log Monitoring

```bash
# View application logs
docker-compose -f docker-compose.prod.yml logs -f web

# View nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx

# View database logs
docker-compose -f docker-compose.prod.yml logs -f db
```

## Backup Configuration

### 1. Automated Backups

Backups are automatically created daily at 2 AM using the backup service in docker-compose.prod.yml.

### 2. Manual Backup

```bash
# Run backup manually
docker-compose -f docker-compose.prod.yml exec backup /app/scripts/backup.sh
```

### 3. Backup Verification

```bash
# List recent backups
ls -lh backups/

# Verify backup integrity
gunzip -t backups/db_backup_YYYYMMDD_HHMMSS.sql.gz
```

### 4. S3 Backup (Optional)

To enable S3 backups:

1. Install AWS CLI
2. Configure AWS credentials
3. Set `BACKUP_S3_BUCKET` environment variable
4. Backups will be automatically uploaded to S3

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database status
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# Check database logs
docker-compose -f docker-compose.prod.yml logs db
```

#### 2. Redis Connection Issues

```bash
# Check Redis status
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Check Redis logs
docker-compose -f docker-compose.prod.yml logs redis
```

#### 3. SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in ssl/cert.pem -text -noout

# Renew certificate
sudo certbot renew
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
docker-compose -f docker-compose.prod.yml restart nginx
```

#### 4. Performance Issues

```bash
# Check resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

### Rollback Procedure

```bash
# Stop all services
docker-compose -f docker-compose.prod.yml down

# Restore from backup
gunzip -c backups/db_backup_YYYYMMDD_HHMMSS.sql.gz | docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -d outerskies_prod

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Emergency Contacts

- **System Administrator**: admin@yourdomain.com
- **Database Administrator**: dba@yourdomain.com
- **Security Team**: security@yourdomain.com

## Security Checklist

- [ ] SSL certificates installed and auto-renewing
- [ ] Firewall configured (ports 80, 443 only)
- [ ] Strong passwords for all services
- [ ] Regular security updates
- [ ] Backup encryption enabled
- [ ] Monitoring and alerting configured
- [ ] Access logs enabled
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] Regular security audits

## Performance Optimization

### 1. Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_chart_user_created ON chart_chart(user_id, created_at);
CREATE INDEX idx_user_email ON chart_user(email);
```

### 2. Cache Optimization

```bash
# Monitor cache hit rates
curl http://localhost/api/v1/system/performance/
```

### 3. Static File Optimization

```bash
# Enable gzip compression
# Already configured in nginx.prod.conf

# Use CDN for static files
# Configure AWS CloudFront or similar
```

## Maintenance

### Regular Tasks

- **Daily**: Check health endpoints and logs
- **Weekly**: Review performance metrics
- **Monthly**: Security updates and audits
- **Quarterly**: Full system backup and restore test

### Update Procedure

```bash
# Pull latest code
git pull origin main

# Run deployment script
./scripts/deploy.sh

# Verify deployment
curl -f http://localhost/health/
```

This completes the production deployment guide. For additional support, refer to the project documentation or contact the development team. 