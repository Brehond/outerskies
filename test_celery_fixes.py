#!/usr/bin/env python3
"""
Test script to verify Celery fixes work correctly.
Tests the new fallback mechanism and API endpoints.
"""

import os
import sys
import requests
import json
import time

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

import django
django.setup()

from chart.celery_utils import is_celery_available, health_check_celery, create_task_with_fallback
from chart.tasks import health_check

def test_celery_utils():
    """Test the new Celery utility functions."""
    print("=== Testing Celery Utility Functions ===")
    
    # Test Celery availability
    available = is_celery_available()
    print(f"Celery available: {available}")
    
    # Test health check
    health_status = health_check_celery()
    print(f"Health status: {health_status['overall_status']}")
    
    # Test synchronous task execution
    try:
        result = health_check.apply()
        print(f"Synchronous task result: {result.result}")
        print("✅ Synchronous task execution works")
    except Exception as e:
        print(f"❌ Synchronous task execution failed: {e}")
    
    # Test task creation with fallback
    try:
        task_result = create_task_with_fallback(
            task_func=health_check,
            args=[],
            task_type='test',
            parameters={'test': True}
        )
        print(f"Task creation result: {task_result}")
        print("✅ Task creation with fallback works")
    except Exception as e:
        print(f"❌ Task creation with fallback failed: {e}")

def test_api_endpoints():
    """Test the API endpoints with the new fallback mechanism."""
    print("\n=== Testing API Endpoints ===")
    
    base_url = "http://localhost:8000"
    
    # Test system health endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/system/health/")
        print(f"System health status: {response.status_code}")
        if response.status_code == 200:
            print("✅ System health endpoint works")
        else:
            print(f"❌ System health endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ System health endpoint error: {e}")
    
    # Test Celery health endpoint
    try:
        response = requests.get(f"{base_url}/api/v1/system/celery_health/")
        print(f"Celery health status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Celery health: {data['data']['overall_status']}")
            print("✅ Celery health endpoint works")
        else:
            print(f"❌ Celery health endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Celery health endpoint error: {e}")

def test_background_task_endpoint():
    """Test a background task endpoint with fallback."""
    print("\n=== Testing Background Task Endpoint ===")
    
    base_url = "http://localhost:8000"
    
    # Test ephemeris calculation endpoint
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/background-charts/calculate_ephemeris/",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"Ephemeris calculation status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print("✅ Background task endpoint works with fallback")
        else:
            print(f"❌ Background task endpoint failed: {response.text}")
    except Exception as e:
        print(f"❌ Background task endpoint error: {e}")

def main():
    """Main test function."""
    print("Testing Celery Fixes for Windows Development")
    print("=" * 50)
    
    # Test utility functions
    test_celery_utils()
    
    # Test API endpoints (if server is running)
    try:
        test_api_endpoints()
        test_background_task_endpoint()
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Django server not running. Start with: python manage.py runserver")
        print("API endpoint tests skipped.")
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nSummary:")
    print("- Celery utility functions should work")
    print("- Fallback mechanism should handle missing Redis/Celery")
    print("- API endpoints should return appropriate responses")
    print("- For development, set CELERY_ALWAYS_EAGER=True in .env")

if __name__ == '__main__':
    main() 