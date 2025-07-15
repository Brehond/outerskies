# CI/CD Pipeline Setup Guide

## Overview

This guide explains how to set up the required GitHub secrets for the CI/CD pipeline to work properly. The pipeline requires several environment variables to be configured as GitHub repository secrets.

## Required GitHub Secrets

### 1. API Authentication Secrets

These are the core API authentication secrets that are **required** for the application to function:

- **`API_KEY`** - Your main API key for authentication
- **`API_SECRET`** - Your API secret for secure communication
- **`ENCRYPTION_KEY`** - Key used for encrypting sensitive data
- **`ENCRYPTION_SALT`** - Salt used for encryption (should be a random string)

### 2. AI Integration Secrets

- **`OPENROUTER_API_KEY`** - API key for OpenRouter AI services

### 3. Payment Processing Secrets

- **`STRIPE_SECRET_KEY`** - Stripe secret key for payment processing
- **`STRIPE_PUBLISHABLE_KEY`** - Stripe publishable key for frontend integration
- **`STRIPE_WEBHOOK_SECRET`** - Secret for verifying Stripe webhooks

## How to Set Up GitHub Secrets

### Step 1: Access Repository Settings

1. Go to your GitHub repository
2. Click on **Settings** tab
3. In the left sidebar, click on **Secrets and variables** → **Actions**

### Step 2: Add Each Secret

For each secret listed above:

1. Click **New repository secret**
2. Enter the **Name** (exactly as shown above)
3. Enter the **Value** (your actual secret value)
4. Click **Add secret**

### Step 3: Verify Secrets

After adding all secrets, you should see them listed in the repository secrets section. The values will be hidden for security.

## Generating Secure Values

### For API Keys and Secrets
```bash
# Generate a random 32-character API key
openssl rand -hex 32

# Generate a random 64-character API secret
openssl rand -hex 64
```

### For Encryption Key and Salt
```bash
# Generate a 32-byte encryption key
openssl rand -base64 32

# Generate a 16-byte encryption salt
openssl rand -base64 16
```

## Testing the Setup

### 1. Trigger a Test Run
- Make a small change to your code
- Push to the `main` or `develop` branch
- Check the Actions tab to see if the CI pipeline runs successfully

### 2. Check for Errors
If the pipeline fails, check the logs for:
- Missing environment variables
- Authentication errors
- Service connection issues

## Troubleshooting Common Issues

### Issue: "API_KEY environment variable must be set"
**Solution:** Ensure you've added the `API_KEY` secret to your GitHub repository secrets.

### Issue: "API_SECRET environment variable must be set"
**Solution:** Ensure you've added the `API_SECRET` secret to your GitHub repository secrets.

### Issue: "ENCRYPTION_KEY environment variable must be set"
**Solution:** Ensure you've added the `ENCRYPTION_KEY` secret to your GitHub repository secrets.

### Issue: "ENCRYPTION_SALT environment variable must be set"
**Solution:** Ensure you've added the `ENCRYPTION_SALT` secret to your GitHub repository secrets.

### Issue: Redis connection failures
**Solution:** The CI pipeline now includes Redis as a service, so this should be resolved.

### Issue: PostgreSQL connection failures
**Solution:** The CI pipeline includes PostgreSQL as a service with proper health checks.

## Security Best Practices

### 1. Never Commit Secrets
- Never add secrets directly to your code
- Always use environment variables or GitHub secrets
- Use `.env` files locally (and keep them out of version control)

### 2. Rotate Secrets Regularly
- Change your API keys and secrets periodically
- Update GitHub secrets when you rotate keys
- Monitor for any unauthorized access

### 3. Use Different Secrets for Different Environments
- Use test/dummy values for CI/CD
- Use production values only in production deployments
- Never use production secrets in development

## Local Development Setup

For local development, create a `.env` file with the same variables:

```env
# API Authentication
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
ENCRYPTION_KEY=your_encryption_key_here
ENCRYPTION_SALT=your_encryption_salt_here

# AI Integration
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Payment Processing
STRIPE_SECRET_KEY=your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key_here
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret_here

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=your_db_name
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your_django_secret_key_here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Redis/Celery
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
```

## CI Pipeline Features

The updated CI pipeline includes:

1. **PostgreSQL Service** - Database for testing
2. **Redis Service** - Cache and message broker for Celery
3. **Service Health Checks** - Ensures services are ready before tests
4. **Comprehensive Environment Variables** - All required secrets configured
5. **Plugin Testing** - Tests all installed plugins
6. **Docker Build** - Builds and tests the Docker image

## Next Steps

After setting up the secrets:

1. **Test the Pipeline** - Make a small change and push to trigger CI
2. **Monitor Results** - Check the Actions tab for successful runs
3. **Review Logs** - Ensure all tests pass and no errors occur
4. **Deploy** - Once CI passes, you can safely deploy to production

## Support

If you encounter issues:

1. Check the GitHub Actions logs for specific error messages
2. Verify all secrets are properly configured
3. Ensure the secret names match exactly (case-sensitive)
4. Test locally with the same environment variables

---

**Note:** Keep your secrets secure and never share them publicly. If you accidentally expose a secret, rotate it immediately. 