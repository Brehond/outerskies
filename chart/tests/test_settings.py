# Test settings
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Basic Django settings
SECRET_KEY = 'test-secret-key-for-testing-purposes-only'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# URLs
ROOT_URLCONF = 'chart.tests.test_urls'

# Apps
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'chart',
    'rest_framework',
    'rest_framework_simplejwt',
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'chart.middleware.request_signing.RequestSigningMiddleware',
    'chart.middleware.auth.APIAuthMiddleware',
    'chart.middleware.encryption.EncryptionMiddleware',
    'chart.middleware.validation.DataValidationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'chart.middleware.rate_limit.RateLimitMiddleware',
]

# Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Security Settings
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Settings
SESSION_COOKIE_AGE = 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_TRUSTED_ORIGINS = [
    'https://outer-skies.com',
    'https://www.outer-skies.com',
    'http://testserver',  # Add testserver for testing
]

# Request Size and Rate Limiting
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
MAX_CONCURRENT_REQUESTS = 5
MEMORY_USAGE_THRESHOLD = 90  # Percentage

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = ("'self'", "https://api.openrouter.ai")

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# JWT settings
JWT_SECRET_KEY = 'test-secret-key'  # In production, use a secure key
JWT_ACCESS_TOKEN_LIFETIME = 60 * 60  # 1 hour
JWT_REFRESH_TOKEN_LIFETIME = 24 * 60 * 60  # 24 hours

# API Settings
API_KEY = 'test-api-key'
API_SECRET = 'test-api-secret'
ENCRYPTION_KEY = 'eXubz67qI7Dj8ZDUS20VEknFK4VW7SmdNlgzp_fbYwM='
ENCRYPTION_SALT = 'test-encryption-salt'
MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB
API_DEPRECATED_VERSIONS = []

# Request Signing Settings
SIGNATURE_HEADER = 'X-Signature'
TIMESTAMP_HEADER = 'X-Timestamp'
NONCE_HEADER = 'X-Nonce'
API_KEY_HEADER = 'X-Api-Key'

# REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': '1.0',
    'ALLOWED_VERSIONS': ['1.0', '2.0'],
    'VERSION_PARAM': 'version',
}

# Rate Limiting Settings
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_QUEUE_TIMEOUT = 30

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB 