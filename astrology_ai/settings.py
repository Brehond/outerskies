from datetime import timedelta
import os
from pathlib import Path
from dotenv import load_dotenv
import sentry_sdk
import platform

load_dotenv()

# Initialize Sentry only if DSN is provided
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn and sentry_dsn != "your_sentry_dsn_here":
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,  # Adjust based on traffic
        send_default_pii=False,
        environment=os.getenv("ENVIRONMENT", "development"),
        # Performance monitoring
        profiles_sample_rate=0.1,
        # Session tracking
        auto_session_tracking=True,
        # Release tracking
        release=os.getenv("GIT_COMMIT_SHA", "unknown"),
    )

BASE_DIR = Path(__file__).resolve().parent.parent

# Enforce production security in non-debug environments
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'test-secret-key-for-ci-only')
if not DEBUG and (not SECRET_KEY or SECRET_KEY == 'test-secret-key-for-ci-only'):
    raise ValueError('SECRET_KEY environment variable must be set in production')
if not DEBUG:
    # Production security enforcement
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
else:
    # Development-only settings
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Parse ALLOWED_HOSTS from environment variable
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")

# Security Headers (always enabled)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Additional Security Headers (from expert analysis)
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_EMBEDDER_POLICY = 'require-corp'

# Audit settings
AUDIT_ENABLED = True

# Performance Monitoring Settings
PERFORMANCE_MONITORING_ENABLED = True
SLOW_QUERY_THRESHOLD = 1.0  # seconds
ERROR_RATE_THRESHOLD = 5.0  # percentage

# Cache Settings (Enhanced for commercial scale)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'outer_skies',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'session',
        'TIMEOUT': 86400,  # 24 hours
    },
    'api': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/3'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 100,
                'retry_on_timeout': True,
            },
        },
        'KEY_PREFIX': 'api',
        'TIMEOUT': 600,  # 10 minutes
    }
}

# Session configuration (enhanced for security and performance)
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Stripe API Keys
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'chart_generation': '10/hour',
        'ai_interpretation': '50/hour',
    },
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
    'DEFAULT_VERSION': 'v1',
    'ALLOWED_VERSIONS': ['v1'],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'core.error_handler.drf_exception_handler',  # Use centralized error handler
    'NON_FIELD_ERRORS_KEY': 'error',
    'DEFAULT_METADATA_CLASS': 'rest_framework.metadata.SimpleMetadata',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,
    'JWK_URL': None,
    'LEEWAY': 0,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
    'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',
    'JTI_CLAIM': 'jti',
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(hours=1),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_celery_results",
    "django_celery_beat",
    "core",  # Add core module
    "api",
    "chart",
    "payments",
    "django_prometheus",
    "tailwind",
    "plugins",
    "plugins.astrology_chat",  # Add back for database migrations
    "monitoring",
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

# Priority 3 Security Settings
# Enhanced security settings
SECURITY_SETTINGS = {
    'RATE_LIMITS': {
        'default': {'requests': 100, 'window': 3600},
        'api': {'requests': 1000, 'window': 3600},
        'chart_generation': {'requests': 10, 'window': 3600},
        'auth': {'requests': 5, 'window': 300},
    },
    'PASSWORD_REQUIREMENTS': {
        'min_length': 12,
        'require_uppercase': True,
        'require_lowercase': True,
        'require_numbers': True,
        'require_special': True,
        'max_similarity': 0.7,
    },
    'ACCOUNT_LOCKOUT': {
        'max_attempts': 5,
        'lockout_duration': 900,  # 15 minutes
        'max_lockouts': 3,
        'permanent_lockout_duration': 86400,  # 24 hours
    },
    'CORS_ALLOWED_ORIGINS': [
        'http://localhost:3000',
        'https://outer-skies.com',
        'https://www.outer-skies.com'
    ],
}

# Update CORS settings
CORS_ALLOWED_ORIGINS = SECURITY_SETTINGS['CORS_ALLOWED_ORIGINS']
CORS_ALLOW_CREDENTIALS = True

# Password Settings (enhanced with Priority 3 requirements)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Increased from 8
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
]

# Middleware Configuration (Updated)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'core.middleware.security.SecurityMiddleware',  # Use consolidated security middleware
    'core.error_handler.ErrorHandlingMiddleware',  # Use centralized error handling
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Phase 3: Production Monitoring and Security Settings
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Phase 1: Consolidated Security Middleware
    'api.middleware.consolidated_security.ConsolidatedSecurityMiddleware',
    
    # Phase 3: Advanced Security Middleware
    'api.middleware.consolidated_security.ConsolidatedSecurityMiddleware',
    
    # Phase 2: Enhanced Performance Monitoring
    'api.middleware.performance_monitor.PerformanceMonitorMiddleware',
    
    # Phase 1: Audit Middleware
    'api.middleware.audit.AuditMiddleware',
]

# Phase 3: Production Monitoring Configuration
PRODUCTION_MONITORING = {
    'ENABLED': True,
    'METRICS_INTERVAL': 60,  # seconds
    'ALERT_EMAIL_RECIPIENTS': [
        'admin@outerskies.com',
        'ops@outerskies.com'
    ],
    'PROMETHEUS_ENABLED': True,
    'SENTRY_ENABLED': True,
}

# Phase 3: Advanced Security Configuration
ADVANCED_SECURITY = {
    'ENABLED': True,
    'RATE_LIMITING': {
        'API': {'requests': 100, 'window': 3600},
        'AUTH': {'requests': 5, 'window': 300},
        'CHART': {'requests': 10, 'window': 3600},
        'DEFAULT': {'requests': 1000, 'window': 3600}
    },
    'THREAT_DETECTION': {
        'ENABLED': True,
        'RISK_THRESHOLD': 0.8,
        'BLOCK_THRESHOLD': 0.9
    },
    'IP_REPUTATION': {
        'ENABLED': True,
        'CACHE_DURATION': 3600,
        'EXTERNAL_SERVICES': ['abuseipdb', 'ipqualityscore']
    }
}

# Phase 3: External Security Services (Optional)
# ABUSEIPDB_API_KEY = 'your_abuseipdb_api_key_here'
# IPQUALITYSCORE_API_KEY = 'your_ipqualityscore_api_key_here'
# GEOIP_PATH = '/path/to/GeoLite2-City.mmdb'

# Phase 3: Sentry Configuration (Optional)
# SENTRY_DSN = 'your_sentry_dsn_here'

# Phase 3: Prometheus Configuration
PROMETHEUS_METRICS = {
    'ENABLED': True,
    'EXPORT_ENDPOINT': '/api/v1/monitoring/prometheus/',
    'COLLECT_DEFAULT_METRICS': True,
    'COLLECT_DJANGO_METRICS': True,
}

# Phase 3: Enhanced Logging Configuration
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
        'security': {
            'format': 'SECURITY {levelname} {asctime} {ip_address} {user_id} {event_type} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'security_filter': {
            '()': 'api.middleware.consolidated_security.ConsolidatedSecurityMiddleware',
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
            'filename': 'logs/outer_skies.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 10,
            'formatter': 'security',
            'filters': ['security_filter'],
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/errors.log',
            'maxBytes': 1024*1024*10,  # 10MB
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
            'level': 'WARNING',
            'propagate': False,
        },
        'api.security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'monitoring': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'chart': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    },
}

# Phase 3: Enhanced Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Phase 3: Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_CONNECT_SRC = ("'self'",)

# Phase 3: Rate Limiting Configuration
RATE_LIMIT_ENABLED = True
RATE_LIMIT_USE_CACHE = True
RATE_LIMIT_CACHE_PREFIX = 'rate_limit'

# Phase 3: Cache Configuration for Monitoring
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
        },
        'KEY_PREFIX': 'outer_skies',
        'TIMEOUT': 300,
    },
    'monitoring': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'monitoring',
        'TIMEOUT': 86400,  # 24 hours for monitoring data
    },
    'security': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/3',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'security',
        'TIMEOUT': 3600,  # 1 hour for security data
    },
}

# Database Configuration - Consolidated and Environment-Aware
def get_database_config():
    """
    Get database configuration based on environment variables.
    Supports DATABASE_URL and individual environment variables.
    """
    import sys
    # Use SQLite in-memory DB for tests
    if any(x in sys.argv[0] for x in ["pytest", "unittest"]) or any(x in sys.argv for x in ["pytest", "unittest"]):
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
            "TEST": {"NAME": ":memory:"},
        }
    # Parse DATABASE_URL if provided
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        
        # Extract database configuration from URL
        db_engine = "django.db.backends.postgresql" if parsed.scheme == "postgres" else "django.db.backends.sqlite3"
        db_name = parsed.path[1:] if parsed.path else "outer_skies"
        db_user = parsed.username or os.getenv("DB_USER", "postgres")
        db_password = parsed.password or os.getenv("DB_PASSWORD", "")
        db_host = parsed.hostname or os.getenv("DB_HOST", "localhost")
        db_port = parsed.port or os.getenv("DB_PORT", "5432")
    else:
        # Fallback to individual environment variables
        db_engine = os.getenv("DB_ENGINE", "django.db.backends.postgresql")
        db_name = os.getenv("DB_NAME", "outer_skies")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")

    # Warn if db_user is root
    if db_user == "root":
        import warnings
        warnings.warn("Database user is set to 'root'. This may cause connection errors if the role does not exist. Please use a dedicated database user.")

    # Base configuration
    config = {
        "ENGINE": db_engine,
        "NAME": db_name,
        "USER": db_user,
        "PASSWORD": db_password,
        "HOST": db_host,
        "PORT": db_port,
        "CONN_MAX_AGE": 600,  # 10 minutes
        "ATOMIC_REQUESTS": False,  # Disable atomic requests for better performance
        "TEST": {
            "NAME": None,  # Use in-memory database for tests
        },
    }

    # PostgreSQL-specific options
    if db_engine == "django.db.backends.postgresql":
        config["OPTIONS"] = {
            "sslmode": "require" if not DEBUG else "disable",
            "connect_timeout": 10,
            "application_name": "outer_skies",
        }
        config["CONN_HEALTH_CHECKS"] = True

    return config

# Set database configuration
DATABASES = {
    "default": get_database_config()
}

# Phase 3: Celery Configuration for Production
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_REJECTS_TASKS = True

# Phase 3: Email Configuration for Alerts
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@outerskies.com')

# Phase 3: Static Files Configuration for Production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# Phase 3: Media Files Configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Phase 3: Session Configuration
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600  # 1 hour

# Phase 3: CSRF Configuration
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'https://outerskies.com',
    'https://www.outerskies.com',
    'https://api.outerskies.com',
]

# Phase 3: Allowed Hosts for Production
ALLOWED_HOSTS = [
    'outerskies.com',
    'www.outerskies.com',
    'api.outerskies.com',
    'localhost',
    '127.0.0.1',
]

# Phase 3: Debug Configuration
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Phase 3: Secret Key Configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = False  # Set to False to maintain current behavior

ROOT_URLCONF = "astrology_ai.urls"

# Build plugin template directories
plugin_template_dirs = []
plugins_dir = os.path.join(BASE_DIR, "plugins")
if os.path.exists(plugins_dir):
    for item in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, item)
        if os.path.isdir(plugin_path) and not item.startswith('_'):
            # Skip management directory
            if item == 'management':
                continue
            # Add template directory if it exists
            template_dir = os.path.join(plugin_path, 'templates')
            if os.path.exists(template_dir):
                plugin_template_dirs.append(template_dir)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "templates"),
            *plugin_template_dirs,  # Add plugin template directories
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "astrology_ai.context_processors.theme_context",
            ],
        },
    },
]

WSGI_APPLICATION = "astrology_ai.wsgi.application"

# Database configuration is now handled by get_database_config() function above

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
        # Priority 3 Security Audit Logging
        'security_audit': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'api.middleware': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
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
API_KEY = os.getenv('API_KEY', 'test-api-key-for-ci-only')
API_SECRET = os.getenv('API_SECRET', 'test-api-secret-for-ci-only')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '3w-9FN3J3p9hR-nHvNVo6Ed96_nzChIUYCpGzq4GPos=')
ENCRYPTION_SALT = os.getenv('ENCRYPTION_SALT', 'test-salt-16chars')

# Validate required environment variables in production
if not DEBUG:
    if not os.getenv('API_KEY') or API_KEY == 'test-api-key-for-ci-only':
        raise ValueError('API_KEY environment variable must be set in production')
    if not os.getenv('API_SECRET') or API_SECRET == 'test-api-secret-for-ci-only':
        raise ValueError('API_SECRET environment variable must be set in production')
    if not os.getenv('ENCRYPTION_KEY') or ENCRYPTION_KEY == '3w-9FN3J3p9hR-nHvNVo6Ed96_nzChIUYCpGzq4GPos=':
        raise ValueError('ENCRYPTION_KEY environment variable must be set in production')
    if not os.getenv('ENCRYPTION_SALT') or ENCRYPTION_SALT == 'test-salt-16chars':
        raise ValueError('ENCRYPTION_SALT environment variable must be set in production')

# Rate Limiting Settings
RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '60'))
RATE_LIMIT_BURST = int(os.getenv('RATE_LIMIT_BURST', '100'))
RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))

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

# DRF Spectacular Settings for API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Outer Skies API',
    'DESCRIPTION': '''
    # Outer Skies - AI-Powered Astrology Chart Analysis API

    This API provides comprehensive astrology chart generation and interpretation services.

    ## Features
    - Birth chart calculation using Swiss Ephemeris
    - AI-powered chart interpretation
    - User authentication and profile management
    - Subscription and payment management
    - Theme system with 75+ color palettes

    ## Authentication
    This API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your_token>
    ```

    ## Rate Limiting
    - Anonymous users: 100 requests/hour
    - Authenticated users: 1000 requests/hour
    - Chart generation: 10 requests/hour
    - AI interpretation: 50 requests/hour

    ## Getting Started
    1. Register a new account using `/api/v1/auth/register/`
    2. Login to get your access token using `/api/v1/auth/login/`
    3. Use the token to access protected endpoints
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'CONTACT': {
        'name': 'Outer Skies Support',
        'email': 'support@outerskies.com',
    },
    'LICENSE': {
        'name': 'MIT License',
        'url': 'https://opensource.org/licenses/MIT',
    },
    'TAGS': [
        {'name': 'authentication', 'description': 'User authentication and authorization'},
        {'name': 'charts', 'description': 'Astrological chart generation and management'},
        {'name': 'interpretations', 'description': 'AI-powered chart interpretations'},
        {'name': 'subscriptions', 'description': 'Subscription and payment management'},
        {'name': 'system', 'description': 'System information and health checks'},
        {'name': 'users', 'description': 'User profile and account management'},
    ],
    'SECURITY': [
        {
            'Bearer': []
        }
    ],
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    'REDOC_UI_SETTINGS': {
        'hideDownloadButton': True,
        'hideHostname': False,
        'hideLoading': False,
    },
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Windows-specific Celery settings
if platform.system() == 'Windows':
    # Windows-specific broker settings
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
        'socket_connect_timeout': 10,
        'socket_timeout': 10,
        'retry_on_timeout': True,
        'max_connections': 20,
        'connection_pool': {
            'max_connections': 20,
            'retry_on_timeout': True,
        }
    }

    # Windows-specific worker settings
    CELERY_WORKER_POOL = 'solo'  # Use solo pool on Windows
    CELERY_WORKER_CONCURRENCY = 1
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1

    # Disable some features that cause issues on Windows
    CELERY_WORKER_DISABLE_RATE_LIMITS = True
    CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

    # Windows-specific result backend settings
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
        'visibility_timeout': 3600,
        'socket_connect_timeout': 10,
        'socket_timeout': 10,
        'retry_on_timeout': True,
    }
else:
    # Linux/Unix settings
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'retry_on_timeout': True,
    }

    CELERY_WORKER_PREFETCH_MULTIPLIER = 1
    CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Broker Connection Settings
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Celery Task Settings
CELERY_TASK_ROUTES = {
    'chart.tasks.generate_chart_task': {'queue': 'chart_generation'},
    'chart.tasks.generate_interpretation_task': {'queue': 'ai_processing'},
    'chart.tasks.calculate_ephemeris_task': {'queue': 'ephemeris'},
}

# Celery Beat Settings (for periodic tasks)
CELERY_BEAT_SCHEDULE = {
    'cleanup-old-tasks': {
        'task': 'chart.tasks.cleanup_old_tasks',
        'schedule': 3600.0,  # Every hour
    },
    'health-check': {
        'task': 'chart.tasks.health_check',
        'schedule': 300.0,  # Every 5 minutes
    },
}

# Celery Task Timeouts
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_TIME_LIMIT = 600  # 10 minutes

# Development environment detection
CELERY_ALWAYS_EAGER = os.getenv('CELERY_ALWAYS_EAGER', 'False').lower() == 'true'
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Redis configuration for background tasks, caching, etc.
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Cache Configuration with Redis fallback


def get_cache_config():
    """Get cache configuration with fallback to local memory if Redis is unavailable."""
    try:
        import redis
        r = redis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=REDIS_DB, 
            password=REDIS_PASSWORD,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        r.ping()
        # Redis is available, use it
        return {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                    'PASSWORD': REDIS_PASSWORD,
                    'CONNECTION_POOL_KWARGS': {
                        'max_connections': 50,
                        'retry_on_timeout': True,
                        'socket_connect_timeout': 5,
                        'socket_timeout': 5,
                        'health_check_interval': 30,
                    },
                    'SOCKET_CONNECT_TIMEOUT': 5,
                    'SOCKET_TIMEOUT': 5,
                    'RETRY_ON_TIMEOUT': True,
                    'MAX_CONNECTIONS': 50,
                    'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
                    'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
                },
                'TIMEOUT': 300,  # 5 minutes default
                'KEY_PREFIX': 'outer_skies',
            }
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Redis not available, falling back to local memory cache: {e}")
        # Redis is not available, use local memory cache
        return {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'unique-snowflake',
                'TIMEOUT': 300,  # 5 minutes
                'OPTIONS': {
                    'MAX_ENTRIES': 1000,
                    'CULL_FREQUENCY': 3,
                }
            }
        }


CACHES = get_cache_config()

# Email Configuration (for development)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
DEFAULT_FROM_EMAIL = 'noreply@outerskies.com'

# For production, use SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
# EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
# EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
# DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@outerskies.com')
