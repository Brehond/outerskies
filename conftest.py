"""
Pytest configuration for Outer Skies tests.
This file ensures Django is properly configured before running tests.
"""

import os
import django
from django.conf import settings

# Set up Django settings for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

# Configure Django
django.setup()

# Import Django test utilities
from django.test import TestCase
from django.test.utils import override_settings

# Configure test settings
def pytest_configure():
    """Configure pytest with Django settings."""
    # Ensure we're using the test database
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
    
    # Disable migrations for faster tests
    settings.MIGRATION_MODULES = {
        'auth': None,
        'contenttypes': None,
        'sessions': None,
        'admin': None,
        'chart': None,
        'payments': None,
        'plugins.astrology_chat': None,
    }
    
    # Use console email backend for tests
    settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    
    # Disable Celery for tests
    settings.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle Django test cases."""
    for item in items:
        # Mark Django test cases
        if isinstance(item, TestCase):
            item.add_marker('django_db') 