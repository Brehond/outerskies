#!/usr/bin/env python3
"""
Test that mimics the web server environment for Celery task queuing.
"""

import os
import django
import requests
import json

# Setup Django exactly like the web server
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.contrib.auth import get_user_model
from chart.tasks import generate_chart_task

User = get_user_model()

def test_web_server_task_queuing():
    """Test task queuing in a web server-like environment."""
    print("Testing web server task queuing...")
    
    try:
        # Create a test user
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
        
        # Test parameters (same as in the API)
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
        
        print(f"Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
        print(f"Celery Broker URL: {settings.CELERY_BROKER_URL}")
        print(f"Celery Result Backend: {settings.CELERY_RESULT_BACKEND}")
        
        # Try to queue a task (same as in the API view)
        print("Attempting to queue task...")
        task = generate_chart_task.delay(test_params)
        print(f"✅ Task queued successfully! Task ID: {task.id}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to queue task: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_web_server_api_call():
    """Test the actual API endpoint to see if it fails."""
    print("\nTesting web server API call...")
    
    try:
        # Start Django test server
        from django.core.management import execute_from_command_line
        import threading
        import time
        
        # This is a simplified test - in reality we'd need to start the server
        # For now, let's just test if the task import works in the web context
        
        # Test the exact same code path as the API
        from api.v1.views import BackgroundChartViewSet
        from rest_framework.test import APIRequestFactory
        from rest_framework.test import force_authenticate
        
        factory = APIRequestFactory()
        
        # Create a request similar to what the API receives
        data = {
            'date': '1990-01-01',
            'time': '12:00',
            'latitude': 45.5,
            'longitude': -64.3,
            'timezone_str': 'America/Halifax',
            'zodiac_type': 'tropical',
            'house_system': 'placidus',
            'model_name': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        request = factory.post('/api/v1/background-charts/generate_chart/', data, format='json')
        force_authenticate(request, user=user)
        
        # Create the viewset and call the method
        viewset = BackgroundChartViewSet()
        viewset.request = request
        
        # This should trigger the same code path as the web server
        response = viewset.generate_chart(request)
        
        if response.status_code == 202:
            print("✅ API call successful!")
            return True
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.data}")
            return False
            
    except Exception as e:
        print(f"❌ API call error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=== Web Server Celery Test ===")
    
    # Test 1: Direct task queuing in web server environment
    task_ok = test_web_server_task_queuing()
    print()
    
    # Test 2: API call simulation
    api_ok = test_web_server_api_call()
    print()
    
    print("=== Summary ===")
    print(f"Direct Task Queuing: {'✅' if task_ok else '❌'}")
    print(f"API Call: {'✅' if api_ok else '❌'}")
    
    if not task_ok:
        print("\n❌ Task queuing fails in web server environment.")
    elif not api_ok:
        print("\n❌ API call fails but direct task queuing works.")
    else:
        print("\n✅ Both tests pass!") 