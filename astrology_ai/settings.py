import os
from pathlib import Path
from dotenv import load_dotenv
import sentry_sdk

load_dotenv()

# Initialize Sentry only if DSN is provided
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn and sentry_dsn != "your_sentry_dsn_here":
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        send_default_pii=False,  # Changed to False for better security
    )

BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError('SECRET_KEY environment variable must be set')

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Parse ALLOWED_HOSTS from environment variable
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Only use these in production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "chart",
    "payments",
    "django_prometheus",
    "tailwind",
    "plugins",
]

# Custom User Model
AUTH_USER_MODEL = 'chart.User'

# Authentication Settings
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/chart/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Session Settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG  # Only secure in production
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Password Settings
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "astrology_ai.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "astrology_ai.wsgi.application"

# Database settings with better error handling
db_engine = os.getenv("DB_ENGINE", "django.db.backends.sqlite3")
DATABASES = {
    "default": {
        "ENGINE": db_engine,
        "NAME": os.getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", ""),
        "PORT": os.getenv("DB_PORT", ""),
        "CONN_MAX_AGE": 600,  # 10 minutes
        "OPTIONS": {
            "timeout": 20,  # 20 seconds
        } if db_engine == "django.db.backends.sqlite3" else {},
    }
}

# Static files configuration
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "chart", "static"),
    os.path.join(BASE_DIR, "static"),
]
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'outer_skies.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'security.log'),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'chart': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'ai_integration': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Plugin System Configuration
PLUGIN_SETTINGS = {
    # Global plugin settings
    'auto_discover': True,
    'auto_install': False,
    'plugin_dir': 'plugins',
    'enabled_plugins': [],  # List of enabled plugins
    'disabled_plugins': [],  # List of disabled plugins
}

# Plugin-specific settings can be added here
# Example:
# PLUGIN_SETTINGS['example_plugin'] = {
#     'api_key': 'your-api-key',
#     'enabled': True,
# }

# Security Settings for Testing
API_KEY = os.getenv('API_KEY', 'test-api-key-for-testing')
API_SECRET = os.getenv('API_SECRET', 'test-api-secret-for-testing')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'test-encryption-key-for-testing-32-chars-long')
ENCRYPTION_SALT = os.getenv('ENCRYPTION_SALT', 'test-salt-for-testing')

# Rate Limiting Settings
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
RATE_LIMIT_BURST = int(os.getenv('RATE_LIMIT_BURST', '100'))

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