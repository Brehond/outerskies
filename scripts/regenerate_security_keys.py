#!/usr/bin/env python3
"""
Security Key Regeneration Script
This script generates new security keys and updates the .env file.
IMPORTANT: Run this script to regenerate all compromised keys.
"""

import os
import secrets
import base64
from cryptography.fernet import Fernet
from pathlib import Path


def generate_secure_key(length=50):
    """Generate a secure random key."""
    return secrets.token_urlsafe(length)


def generate_encryption_key():
    """Generate a secure encryption key."""
    return Fernet.generate_key().decode()


def generate_encryption_salt():
    """Generate a secure encryption salt."""
    return secrets.token_bytes(16).hex()


def backup_env_file():
    """Create a backup of the current .env file."""
    env_path = Path('.env')
    if env_path.exists():
        backup_path = Path('.env.backup')
        with open(env_path, 'r') as src, open(backup_path, 'w') as dst:
            dst.write(src.read())
        print("\u2705 Backed up .env to .env.backup")


def regenerate_env_file():
    """Generate a new .env file with fresh security keys."""

    # Generate new security keys
    new_secret_key = generate_secure_key(50)
    new_api_key = generate_secure_key(32)
    new_api_secret = generate_secure_key(64)
    new_encryption_key = generate_encryption_key()
    new_encryption_salt = generate_encryption_salt()
    new_db_password = generate_secure_key(32)
    new_redis_password = generate_secure_key(32)

    # Create new .env content
    env_content = f"""# Django Settings
SECRET_KEY={new_secret_key}
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Settings
DB_ENGINE=django.db.backends.postgresql
DB_NAME=outer_skies
DB_USER=outer_skies_user
DB_PASSWORD={new_db_password}
DB_HOST=localhost
DB_PORT=5432

# OpenRouter AI API - REGENERATE THIS KEY
OPENROUTER_API_KEY=your_new_openrouter_api_key

# Stripe Payment Settings - UPDATE WITH REAL KEYS
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret

# Security Settings
API_KEY={new_api_key}
API_SECRET={new_api_secret}
ENCRYPTION_KEY={new_encryption_key}
ENCRYPTION_SALT={new_encryption_salt}

# Redis Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD={new_redis_password}

# Email Settings (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_specific_password

# AWS Settings (optional)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-1

# Sentry Error Tracking (optional)
SENTRY_DSN=your_sentry_dsn_here
"""

    # Write new .env file
    with open('.env', 'w') as f:
        f.write(env_content)

    print("✅ Generated new .env file with fresh security keys")
    print("\n⚠️  IMPORTANT ACTIONS REQUIRED:")
    print("1. Regenerate your OpenRouter API key at https://openrouter.ai/")
    print("2. Update Stripe keys with your real Stripe credentials")
    print("3. Update email settings if you want email functionality")
    print("4. Update AWS settings if you want S3 storage")
    print("5. Update Sentry DSN if you want error tracking")
    print("\n🔒 Security keys generated:")
    print(f"   - SECRET_KEY: {new_secret_key[:20]}...")
    print(f"   - API_KEY: {new_api_key[:20]}...")
    print(f"   - API_SECRET: {new_api_secret[:20]}...")
    print(f"   - ENCRYPTION_KEY: {new_encryption_key[:20]}...")
    print(f"   - DB_PASSWORD: {new_db_password[:20]}...")


def main():
    """Main function to regenerate security keys."""
    print("🔐 Security Key Regeneration Script")
    print("=" * 50)

    # Check if .env exists
    if not Path('.env').exists():
        print("❌ .env file not found. Creating new one...")
        regenerate_env_file()
        return

    # Backup existing .env
    backup_env_file()

    # Regenerate keys
    regenerate_env_file()

    print("\n✅ Security key regeneration complete!")
    print("📝 Review the generated .env file and update with your real credentials.")
    print("🔒 Keep your .env file secure and never commit it to version control.")


if __name__ == "__main__":
    main()
