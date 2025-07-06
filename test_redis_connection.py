#!/usr/bin/env python3
"""
Test script to check Redis connectivity for Django and Celery.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.conf import settings
from django.core.cache import cache
from celery import Celery

def test_django_redis_connection():
    """Test if Django can connect to Redis for caching."""
    print("Testing Django Redis connection...")
    try:
        # Test cache connection
        cache.set('test_key', 'test_value', timeout=60)
        result = cache.get('test_key')
        if result == 'test_value':
            print("✅ Django Redis cache connection: SUCCESS")
            return True
        else:
            print("❌ Django Redis cache connection: FAILED - Cache not working")
            return False
    except Exception as e:
        print(f"❌ Django Redis cache connection: FAILED - {e}")
        return False

def test_celery_redis_connection():
    """Test if Celery can connect to Redis for task queuing."""
    print("Testing Celery Redis connection...")
    try:
        # Import the Celery app from the project
        from astrology_ai.celery import app
        
        # Test broker connection by trying to inspect the broker
        from celery.backends.redis import RedisBackend
        backend = RedisBackend(app=app)
        
        # Get the Redis client from the backend
        redis_client = backend.client
        redis_client.ping()
        print("✅ Celery Redis broker connection: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Celery Redis broker connection: FAILED - {e}")
        return False

def test_redis_direct_connection():
    """Test direct Redis connection."""
    print("Testing direct Redis connection...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Direct Redis connection: SUCCESS")
        return True
    except Exception as e:
        print(f"❌ Direct Redis connection: FAILED - {e}")
        return False

def main():
    print("=== Redis Connection Tests ===")
    print(f"Redis Host: {settings.REDIS_HOST}")
    print(f"Redis Port: {settings.REDIS_PORT}")
    print(f"Redis DB: {settings.REDIS_DB}")
    print(f"Celery Broker URL: {settings.CELERY_BROKER_URL}")
    print(f"Celery Result Backend: {settings.CELERY_RESULT_BACKEND}")
    print()
    
    # Run tests
    direct_ok = test_redis_direct_connection()
    print()
    
    django_ok = test_django_redis_connection()
    print()
    
    celery_ok = test_celery_redis_connection()
    print()
    
    # Summary
    print("=== Summary ===")
    print(f"Direct Redis: {'✅' if direct_ok else '❌'}")
    print(f"Django Cache: {'✅' if django_ok else '❌'}")
    print(f"Celery Broker: {'✅' if celery_ok else '❌'}")
    
    if not direct_ok:
        print("\n❌ Redis is not accessible directly. Check if Redis is running.")
    elif not django_ok:
        print("\n❌ Django cannot connect to Redis cache. Check django-redis configuration.")
    elif not celery_ok:
        print("\n❌ Celery cannot connect to Redis broker. Check Celery configuration.")
    else:
        print("\n✅ All Redis connections working!")

if __name__ == "__main__":
    main() 