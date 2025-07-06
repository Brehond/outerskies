#!/usr/bin/env python3
"""
Debug Redis connection settings in different contexts.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.conf import settings
from astrology_ai.celery import app
import redis

def debug_redis_connections():
    """Debug Redis connection settings."""
    print("=== Redis Connection Debug ===")
    
    print(f"Environment DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    print(f"Environment CELERY_BROKER_URL: {os.environ.get('CELERY_BROKER_URL')}")
    print(f"Environment REDIS_HOST: {os.environ.get('REDIS_HOST')}")
    print(f"Environment REDIS_PORT: {os.environ.get('REDIS_PORT')}")
    print()
    
    print("Django Settings:")
    print(f"  REDIS_HOST: {settings.REDIS_HOST}")
    print(f"  REDIS_PORT: {settings.REDIS_PORT}")
    print(f"  REDIS_DB: {settings.REDIS_DB}")
    print(f"  REDIS_PASSWORD: {settings.REDIS_PASSWORD}")
    print(f"  CELERY_BROKER_URL: {settings.CELERY_BROKER_URL}")
    print(f"  CELERY_RESULT_BACKEND: {settings.CELERY_RESULT_BACKEND}")
    print()
    
    print("Celery App Settings:")
    print(f"  App Broker URL: {app.conf.broker_url}")
    print(f"  App Result Backend: {app.conf.result_backend}")
    print()
    
    print("Cache Settings:")
    print(f"  Cache Location: {settings.CACHES['default']['LOCATION']}")
    print(f"  Cache Options: {settings.CACHES['default']['OPTIONS']}")
    print()
    
    # Test direct Redis connection
    print("Testing direct Redis connections...")
    try:
        # Test with settings
        r1 = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD
        )
        r1.ping()
        print("✅ Direct Redis connection with settings: SUCCESS")
    except Exception as e:
        print(f"❌ Direct Redis connection with settings: FAILED - {e}")
    
    try:
        # Test with localhost
        r2 = redis.Redis(host='localhost', port=6379, db=0)
        r2.ping()
        print("✅ Direct Redis connection with localhost: SUCCESS")
    except Exception as e:
        print(f"❌ Direct Redis connection with localhost: FAILED - {e}")
    
    try:
        # Test with broker URL
        import urllib.parse
        broker_url = settings.CELERY_BROKER_URL
        parsed = urllib.parse.urlparse(broker_url)
        r3 = redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            db=int(parsed.path[1:]) if parsed.path else 0,
            password=parsed.password
        )
        r3.ping()
        print("✅ Direct Redis connection with broker URL: SUCCESS")
    except Exception as e:
        print(f"❌ Direct Redis connection with broker URL: FAILED - {e}")

if __name__ == "__main__":
    debug_redis_connections() 