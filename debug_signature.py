#!/usr/bin/env python3
"""
Debug script to compare client and server signature generation for POST requests.
"""

import requests
import json
import hmac
import hashlib
import base64
import random
import string
import time

API_SECRET = 'test-api-secret-for-testing'

def generate_signature(method, path, query_string, timestamp, nonce, body=''):
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
    print(f"DEBUG: Signature string: {repr(signature_string)}")
    return hmac.new(
        API_SECRET.encode(),
        signature_string.encode(),
        hashlib.sha256
    ).hexdigest()

def debug_signature_generation():
    """Debug the signature generation process."""
    print("=== DEBUGGING SIGNATURE GENERATION ===")
    
    # Test data
    method = 'POST'
    path = '/api/v1/background-charts/calculate_ephemeris/'
    query_string = ''
    timestamp = str(int(time.time()))
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    print(f"Method: {method}")
    print(f"Path: {path}")
    print(f"Query string: {query_string}")
    print(f"Timestamp: {timestamp}")
    print(f"Nonce: {nonce}")
    print(f"Test data: {test_data}")
    
    # Method 1: JSON with separators
    json_str = json.dumps(test_data, separators=(",", ":"))
    body_bytes = json_str.encode('utf-8')
    body_b64 = base64.b64encode(body_bytes).decode('utf-8')
    
    print(f"\nMethod 1 - JSON with separators:")
    print(f"JSON string: {json_str}")
    print(f"Body bytes: {body_bytes}")
    print(f"Body base64: {body_b64}")
    
    signature1 = generate_signature(method, path, query_string, timestamp, nonce, body_b64)
    print(f"Signature 1: {signature1}")
    
    # Method 2: JSON with default formatting
    json_str2 = json.dumps(test_data)
    body_bytes2 = json_str2.encode('utf-8')
    body_b64_2 = base64.b64encode(body_bytes2).decode('utf-8')
    
    print(f"\nMethod 2 - JSON with default formatting:")
    print(f"JSON string: {json_str2}")
    print(f"Body bytes: {body_bytes2}")
    print(f"Body base64: {body_b64_2}")
    
    signature2 = generate_signature(method, path, query_string, timestamp, nonce, body_b64_2)
    print(f"Signature 2: {signature2}")
    
    # Method 3: Raw string
    body_str3 = str(test_data)
    body_bytes3 = body_str3.encode('utf-8')
    body_b64_3 = base64.b64encode(body_bytes3).decode('utf-8')
    
    print(f"\nMethod 3 - Raw string:")
    print(f"Body string: {body_str3}")
    print(f"Body bytes: {body_bytes3}")
    print(f"Body base64: {body_b64_3}")
    
    signature3 = generate_signature(method, path, query_string, timestamp, nonce, body_b64_3)
    print(f"Signature 3: {signature3}")
    
    return {
        'timestamp': timestamp,
        'nonce': nonce,
        'signatures': {
            'method1': signature1,
            'method2': signature2,
            'method3': signature3
        },
        'bodies': {
            'method1': body_b64,
            'method2': body_b64_2,
            'method3': body_b64_3
        }
    }

def test_all_signature_methods():
    """Test all signature methods against the server."""
    print("\n=== TESTING ALL SIGNATURE METHODS ===")
    
    debug_info = debug_signature_generation()
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
    
    for method_name, signature in debug_info['signatures'].items():
        print(f"\nTesting {method_name}:")
        headers = {
            'X-Signature': signature,
            'X-Timestamp': debug_info['timestamp'],
            'X-Nonce': debug_info['nonce'],
            'X-API-Key': 'test-api-key-for-testing',
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(f"{base_url}{path}", json=test_data, headers=headers)
            print(f"  Status: {response.status_code}")
            if response.status_code in [200, 202]:
                print(f"  ✅ SUCCESS with {method_name}")
                return method_name
            else:
                print(f"  ❌ FAILED: {response.text}")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    return None

def test_with_server_logs():
    """Test and capture server logs to see what the server expects."""
    print("\n=== TESTING WITH SERVER LOGS ===")
    
    # Generate a fresh signature
    timestamp = str(int(time.time()))
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    # Use the working method from our tests
    json_str = json.dumps(test_data, separators=(",", ":"))
    body_bytes = json_str.encode('utf-8')
    body_b64 = base64.b64encode(body_bytes).decode('utf-8')
    
    signature = generate_signature('POST', '/api/v1/background-charts/calculate_ephemeris/', '', timestamp, nonce, body_b64)
    
    print(f"Timestamp: {timestamp}")
    print(f"Nonce: {nonce}")
    print(f"Body base64: {body_b64}")
    print(f"Generated signature: {signature}")
    
    # Make the request
    base_url = "http://localhost:8000"
    path = "/api/v1/background-charts/calculate_ephemeris/"
    headers = {
        'X-Signature': signature,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-API-Key': 'test-api-key-for-testing',
        'Content-Type': 'application/json',
    }
    
    try:
        response = requests.post(f"{base_url}{path}", json=test_data, headers=headers)
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
    except Exception as e:
        print(f"Request error: {e}")

if __name__ == '__main__':
    # Test all signature methods
    working_method = test_all_signature_methods()
    
    if working_method:
        print(f"\n🎉 Found working signature method: {working_method}")
    else:
        print(f"\n❌ No signature method worked. Testing with server logs...")
        test_with_server_logs() 