import os
import secrets
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

def generate_api_key():
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

def generate_api_secret():
    """Generate a secure API secret."""
    return secrets.token_urlsafe(64)

def generate_encryption_key():
    """Generate a secure encryption key."""
    return Fernet.generate_key().decode()

def generate_encryption_salt():
    """Generate a secure encryption salt."""
    return secrets.token_bytes(16).hex()

def main():
    """Generate security keys and create .env file."""
    # Generate keys
    api_key = generate_api_key()
    api_secret = generate_api_secret()
    encryption_key = generate_encryption_key()
    encryption_salt = generate_encryption_salt()
    
    # Create .env file
    env_content = f"""# Security Keys
API_KEY={api_key}
API_SECRET={api_secret}
ENCRYPTION_KEY={encryption_key}
ENCRYPTION_SALT={encryption_salt}

# Django Settings
DEBUG=False
SECRET_KEY={secrets.token_urlsafe(50)}
ALLOWED_HOSTS=outer-skies.com,www.outer-skies.com

# Database Settings
DB_NAME=outer_skies
DB_USER=outer_skies_user
DB_PASSWORD={secrets.token_urlsafe(32)}
DB_HOST=localhost
DB_PORT=5432

# Email Settings
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password

# Redis Settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD={secrets.token_urlsafe(32)}

# AWS Settings
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=outer-skies-media
AWS_S3_REGION_NAME=us-east-1

# Stripe Settings
STRIPE_PUBLIC_KEY=your-stripe-public-key
STRIPE_SECRET_KEY=your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
"""
    
    # Write to .env file
    with open('.env', 'w') as f:
        f.write(env_content)
        
    print("Security keys generated and .env file created successfully!")
    print("\nIMPORTANT: Please update the following settings in the .env file:")
    print("1. Email settings with your SMTP credentials")
    print("2. Database settings with your database credentials")
    print("3. AWS settings with your AWS credentials")
    print("4. Stripe settings with your Stripe credentials")
    print("\nAlso, make sure to:")
    print("1. Add .env to .gitignore")
    print("2. Keep these keys secure and never commit them to version control")
    print("3. Use different keys for development and production environments")

if __name__ == '__main__':
    main() 