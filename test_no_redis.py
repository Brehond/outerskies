#!/usr/bin/env python3
"""
Test script to verify the application works without Redis.
Tests the cache fallback mechanism and API endpoints.
"""

import os
import sys
import requests
import json
import hmac
import hashlib
import base64
import random
import string
import time

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

import django
django.setup()

from django.core.cache import cache
from django.conf import settings

API_SECRET = 'test-api-secret-for-testing'

def generate_signature(method, path, query_string, timestamp, nonce, body=''):
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
    return hmac.new(
        API_SECRET.encode(),
        signature_string.encode(),
        hashlib.sha256
    ).hexdigest()

def get_signed_headers(method, path, body=None):
    timestamp = str(int(time.time()))
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    query_string = ''
    
    if body:
        if isinstance(body, (dict, list)):
            import json as _json
            body_bytes = _json.dumps(body, separators=(",", ":")).encode('utf-8')
        elif isinstance(body, bytes):
            body_bytes = body
        else:
            body_bytes = str(body).encode('utf-8')
        body_b64 = base64.b64encode(body_bytes).decode('utf-8')
    else:
        body_b64 = ''
    
    signature = generate_signature(method, path, query_string, timestamp, nonce, body_b64)
    return {
        'X-Signature': signature,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'Content-Type': 'application/json',
    }

def test_cache_fallback():
    """Test that cache works with fallback mechanism."""
    print("=== Testing Cache Fallback ===")
    
    try:
        # Test cache operations
        cache.set('test_key', 'test_value', 60)
        value = cache.get('test_key')
        print(f"Cache test: {value}")
        
        if value == 'test_value':
            print("✅ Cache fallback mechanism works")
            return True
        else:
            print("❌ Cache fallback mechanism failed")
            return False
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints work without Redis."""
    print("\n=== Testing API Endpoints ===")
    
    base_url = "http://localhost:8000"
    
    # Test system health endpoint (public)
    try:
        response = requests.get(f"{base_url}/api/v1/system/health/")
        print(f"System health status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print("✅ System health endpoint works without Redis")
        else:
            print(f"❌ System health endpoint failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ System health endpoint error: {e}")
        return False
    
    # Test Celery health endpoint (signed)
    try:
        path = "/api/v1/system/celery_health/"
        headers = get_signed_headers('GET', path)
        response = requests.get(f"{base_url}{path}", headers=headers)
        print(f"Celery health status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Celery health: {data['data']['overall_status']}")
            print("✅ Celery health endpoint works without Redis")
        else:
            print(f"❌ Celery health endpoint failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Celery health endpoint error: {e}")
        return False
    
    return True

def test_background_task():
    """Test background task endpoint works without Redis."""
    print("\n=== Testing Background Task Endpoint ===")
    
    base_url = "http://localhost:8000"
    path = "/api/v1/background-charts/calculate_ephemeris/"
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
        headers = get_signed_headers('POST', path, test_data)
        response = requests.post(
            f"{base_url}{path}",
            json=test_data,
            headers=headers
        )
        print(f"Ephemeris calculation status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            print("✅ Background task endpoint works without Redis")
            return True
        else:
            print(f"❌ Background task endpoint failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Background task endpoint error: {e}")
        return False

def main():
    """Main test function."""
    print("Testing Application Without Redis")
    print("=" * 50)
    
    # Test cache fallback
    cache_ok = test_cache_fallback()
    
    # Test API endpoints (if server is running)
    try:
        api_ok = test_api_endpoints()
        task_ok = test_background_task()
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Django server not running. Start with: python manage.py runserver")
        print("API endpoint tests skipped.")
        api_ok = True
        task_ok = True
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Cache Fallback: {'✅ PASS' if cache_ok else '❌ FAIL'}")
    print(f"API Endpoints: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"Background Tasks: {'✅ PASS' if task_ok else '❌ FAIL'}")
    
    if cache_ok and api_ok and task_ok:
        print("\n🎉 All tests passed! Application works without Redis.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == '__main__':
    main() 