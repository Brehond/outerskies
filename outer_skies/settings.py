# Security Settings
import os
SECURE_SSL_REDIRECT = True  # Redirect all HTTP to HTTPS
SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
CSRF_COOKIE_SECURE = True  # Only send CSRF cookies over HTTPS
SECURE_BROWSER_XSS_FILTER = True  # Enable XSS filtering
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME type sniffing
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Settings
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'https://outer-skies.com',
    'https://www.outer-skies.com',
]

# Request Size and Rate Limiting
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
MAX_CONCURRENT_REQUESTS = 5
MEMORY_USAGE_THRESHOLD = 90  # Percentage

# Add Security Middleware
MIDDLEWARE = [
    'monitoring.performance_monitor.PerformanceMonitoringMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'chart.middleware.security.EnhancedSecurityMiddleware',
    'chart.middleware.rate_limit.RateLimitMiddleware',
    'chart.middleware.auth.APIAuthMiddleware',
    'chart.middleware.validation.DataValidationMiddleware',
    'chart.middleware.password.PasswordSecurityMiddleware',
    'chart.middleware.file_upload.FileUploadSecurityMiddleware',
    'chart.middleware.error_handling.ErrorHandlingMiddleware',
    'chart.middleware.session.SessionSecurityMiddleware',
    'chart.middleware.api_version.APIVersionMiddleware',
    'chart.middleware.request_signing.RequestSigningMiddleware',
    'chart.middleware.encryption.EncryptionMiddleware',
    'csp.middleware.CSPMiddleware',
]

# CORS Settings
CORS_ALLOWED_ORIGINS = [
    "https://outer-skies.com",
    "https://www.outer-skies.com",
]
CORS_ALLOW_CREDENTIALS = True

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "'unsafe-eval'")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = ("'self'", "https://api.openrouter.ai")

# Password Security Settings
PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_NUMBERS = True
PASSWORD_REQUIRE_SPECIAL = True
PASSWORD_MAX_AGE = 90  # days
PASSWORD_HISTORY_SIZE = 5
PASSWORD_MAX_ATTEMPTS = 5
PASSWORD_LOCKOUT_TIME = 15  # minutes

# File Upload Settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_UPLOAD_TYPES = {
    'image/jpeg', 'image/png', 'image/gif',
    'application/pdf', 'text/plain', 'text/csv',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}
BLOCKED_UPLOAD_EXTENSIONS = {
    '.exe', '.dll', '.bat', '.cmd', '.sh', '.php', '.asp', '.aspx',
    '.jsp', '.js', '.vbs', '.ps1', '.py', '.rb', '.pl'
}
SCAN_UPLOADED_FILES = True
SANITIZE_UPLOADED_FILES = True

# Error Handling Settings
ERROR_EMAIL = 'admin@example.com'
ERROR_THRESHOLD = 5  # errors per minute
ERROR_WINDOW = 60  # seconds
TRACK_ERRORS = True
REPORT_ERRORS = True

# Session Security Settings
SESSION_ROTATION = 300  # 5 minutes
MAX_SESSION_ATTEMPTS = 5
SESSION_LOCKOUT_TIME = 900  # 15 minutes

# API Version Settings
API_CURRENT_VERSION = '1.0'
API_MIN_VERSION = '1.0'
API_MAX_VERSION = '2.0'
API_DEPRECATED_VERSIONS = []
API_VERSION_HEADER = 'X-API-Version'

# Request Signing Settings
API_KEY = ''  # Set this in environment variables
API_SECRET = ''  # Set this in environment variables
SIGNATURE_HEADER = 'X-Signature'
TIMESTAMP_HEADER = 'X-Timestamp'
NONCE_HEADER = 'X-Nonce'
TIMESTAMP_WINDOW = 300  # 5 minutes
NONCE_EXPIRY = 3600  # 1 hour

# Encryption Settings
ENCRYPTION_KEY = ''  # Set this in environment variables
ENCRYPTION_SALT = ''  # Set this in environment variables
ENCRYPTION_HEADER = 'X-Encryption'
ENCRYPTION_ALGORITHM = 'AES-256-GCM'
KEY_ROTATION_INTERVAL = 86400  # 24 hours

# Public API Paths
PUBLIC_API_PATHS = [
    '/api/health/',
    '/api/public/',
    '/api/docs/',
]

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'chart.middleware': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# ... rest of existing settings ...
