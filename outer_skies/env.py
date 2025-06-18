import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

def get_env_variable(var_name, default=None):
    """Get environment variable or return default value."""
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f'Environment variable {var_name} is not set')
    return value

# Security Keys
API_KEY = get_env_variable('API_KEY')
API_SECRET = get_env_variable('API_SECRET')
ENCRYPTION_KEY = get_env_variable('ENCRYPTION_KEY')
ENCRYPTION_SALT = get_env_variable('ENCRYPTION_SALT')

# Django Settings
DEBUG = get_env_variable('DEBUG', 'False').lower() == 'true'
SECRET_KEY = get_env_variable('SECRET_KEY')
ALLOWED_HOSTS = get_env_variable('ALLOWED_HOSTS').split(',')

# Database Settings
DB_NAME = get_env_variable('DB_NAME')
DB_USER = get_env_variable('DB_USER')
DB_PASSWORD = get_env_variable('DB_PASSWORD')
DB_HOST = get_env_variable('DB_HOST')
DB_PORT = get_env_variable('DB_PORT')

# Email Settings
EMAIL_HOST = get_env_variable('EMAIL_HOST')
EMAIL_PORT = int(get_env_variable('EMAIL_PORT'))
EMAIL_USE_TLS = get_env_variable('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = get_env_variable('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = get_env_variable('EMAIL_HOST_PASSWORD')

# Redis Settings
REDIS_HOST = get_env_variable('REDIS_HOST')
REDIS_PORT = int(get_env_variable('REDIS_PORT'))
REDIS_PASSWORD = get_env_variable('REDIS_PASSWORD')

# AWS Settings
AWS_ACCESS_KEY_ID = get_env_variable('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = get_env_variable('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = get_env_variable('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = get_env_variable('AWS_S3_REGION_NAME')

# Stripe Settings
STRIPE_PUBLIC_KEY = get_env_variable('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY = get_env_variable('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = get_env_variable('STRIPE_WEBHOOK_SECRET') 