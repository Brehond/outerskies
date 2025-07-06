#!/usr/bin/env python3
"""
Debug script to test middleware chain and isolate the task creation issue.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.test import RequestFactory
from django.http import HttpResponse
from chart.middleware.request_signing import RequestSigningMiddleware
from chart.middleware.auth import APIAuthMiddleware
from chart.celery_utils import create_task_with_fallback
from chart.tasks import calculate_ephemeris_task

def test_middleware_chain():
    """Test the middleware chain to see where the error occurs."""
    print("Testing middleware chain...")
    
    # Create a simple view function
    def test_view(request):
        return HttpResponse("Test view")
    
    # Create request factory
    factory = RequestFactory()
    
    # Test data
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    # Create request
    request = factory.post('/api/v1/background-charts/calculate_ephemeris/', 
                          data=test_data,
                          content_type='application/json')
    
    # Add headers
    request.headers = {
        'X-Signature': 'test-signature',
        'X-Timestamp': '1750809973',
        'X-Nonce': '4aNWxJYR4pfv',
        'X-API-Key': 'test-api-key-for-testing',
        'Content-Type': 'application/json'
    }
    
    print("1. Testing RequestSigningMiddleware...")
    try:
        signing_middleware = RequestSigningMiddleware(test_view)
        response = signing_middleware(request)
        print(f"   ✅ RequestSigningMiddleware passed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ RequestSigningMiddleware failed: {e}")
        return
    
    print("2. Testing APIAuthMiddleware...")
    try:
        auth_middleware = APIAuthMiddleware(test_view)
        response = auth_middleware(request)
        print(f"   ✅ APIAuthMiddleware passed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ APIAuthMiddleware failed: {e}")
        return
    
    print("3. Testing create_task_with_fallback directly...")
    try:
        ephemeris_params = {
            'utc_date': '1990-01-01',
            'utc_time': '17:00:00',
            'latitude': 45.5,
            'longitude': -64.3,
            'zodiac_type': 'tropical',
            'house_system': 'placidus'
        }
        
        task_result = create_task_with_fallback(
            task_func=calculate_ephemeris_task,
            args=[ephemeris_params],
            user=None,
            task_type='ephemeris',
            parameters=ephemeris_params
        )
        
        print(f"   ✅ create_task_with_fallback passed: {task_result}")
    except Exception as e:
        print(f"   ❌ create_task_with_fallback failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("✅ All middleware tests passed!")

if __name__ == '__main__':
    test_middleware_chain() 