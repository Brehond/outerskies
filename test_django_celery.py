#!/usr/bin/env python3
"""
Test Django's ability to queue Celery tasks.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.conf import settings
from astrology_ai.celery import app
from chart.tasks import generate_chart_task

def test_django_celery_connection():
    """Test if Django can queue Celery tasks."""
    print("Testing Django Celery task queuing...")
    
    try:
        # Test parameters
        test_params = {
            'utc_date': '1990-01-01',
            'utc_time': '12:00:00',
            'latitude': 45.5,
            'longitude': -64.3,
            'zodiac_type': 'tropical',
            'house_system': 'placidus',
            'model_name': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 1000,
            'location': 'Test Location'
        }
        
        print(f"Celery Broker URL: {settings.CELERY_BROKER_URL}")
        print(f"Celery Result Backend: {settings.CELERY_RESULT_BACKEND}")
        print(f"App Broker URL: {app.conf.broker_url}")
        print(f"App Result Backend: {app.conf.result_backend}")
        
        # Try to queue a task
        print("Attempting to queue task...")
        task = generate_chart_task.delay(test_params)
        print(f"✅ Task queued successfully! Task ID: {task.id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to queue task: {e}")
        print(f"Error type: {type(e)}")
        return False

def test_celery_app_config():
    """Test Celery app configuration."""
    print("\nTesting Celery app configuration...")
    
    try:
        print(f"App name: {app.main}")
        print(f"Broker URL: {app.conf.broker_url}")
        print(f"Result Backend: {app.conf.result_backend}")
        print(f"Task Serializer: {app.conf.task_serializer}")
        print(f"Result Serializer: {app.conf.result_serializer}")
        print(f"Accept Content: {app.conf.accept_content}")
        
        # Test broker connection
        from celery.backends.redis import RedisBackend
        backend = RedisBackend(app=app)
        redis_client = backend.client
        redis_client.ping()
        print("✅ Celery app can connect to Redis")
        return True
        
    except Exception as e:
        print(f"❌ Celery app configuration error: {e}")
        return False

if __name__ == "__main__":
    print("=== Django Celery Connection Test ===")
    
    config_ok = test_celery_app_config()
    print()
    
    if config_ok:
        task_ok = test_django_celery_connection()
        print()
        
        print("=== Summary ===")
        print(f"Celery Config: {'✅' if config_ok else '❌'}")
        print(f"Task Queuing: {'✅' if task_ok else '❌'}")
        
        if not task_ok:
            print("\n❌ Django cannot queue Celery tasks. Check broker configuration.")
        else:
            print("\n✅ Django can queue Celery tasks successfully!")
    else:
        print("\n❌ Celery app configuration is invalid.") 