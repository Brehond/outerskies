#!/usr/bin/env python3
"""
Debug script to compare client and server body handling.
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
API_KEY = 'test-api-key-for-testing'

def generate_signature(method, path, query_string, timestamp, nonce, body=''):
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
    print(f"CLIENT: Signature string: {repr(signature_string)}")
    return hmac.new(
        API_SECRET.encode(),
        signature_string.encode(),
        hashlib.sha256
    ).hexdigest()

def test_body_comparison():
    """Test to see exact body differences."""
    print("=== BODY COMPARISON TEST ===")
    
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
    
    # Method 1: JSON with separators (current method)
    json_str1 = json.dumps(test_data, separators=(",", ":"))
    body_bytes1 = json_str1.encode('utf-8')
    body_b64_1 = base64.b64encode(body_bytes1).decode('utf-8')
    
    print(f"Method 1 - JSON with separators:")
    print(f"  JSON string: {repr(json_str1)}")
    print(f"  Body bytes: {body_bytes1}")
    print(f"  Body base64: {body_b64_1}")
    
    # Method 2: JSON with default formatting
    json_str2 = json.dumps(test_data)
    body_bytes2 = json_str2.encode('utf-8')
    body_b64_2 = base64.b64encode(body_bytes2).decode('utf-8')
    
    print(f"\nMethod 2 - JSON with default formatting:")
    print(f"  JSON string: {repr(json_str2)}")
    print(f"  Body bytes: {body_bytes2}")
    print(f"  Body base64: {body_b64_2}")
    
    # Method 3: Raw string
    body_str3 = str(test_data)
    body_bytes3 = body_str3.encode('utf-8')
    body_b64_3 = base64.b64encode(body_bytes3).decode('utf-8')
    
    print(f"\nMethod 3 - Raw string:")
    print(f"  Body string: {repr(body_str3)}")
    print(f"  Body bytes: {body_bytes3}")
    print(f"  Body base64: {body_b64_3}")
    
    # Test with requests to see what actually gets sent
    print(f"\n=== TESTING WITH REQUESTS ===")
    
    timestamp = str(int(time.time()))
    nonce = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    path = "/api/v1/background-charts/calculate_ephemeris/"
    
    # Test with Method 1 (current)
    signature1 = generate_signature('POST', path, '', timestamp, nonce, body_b64_1)
    
    headers = {
        'X-Signature': signature1,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
    }
    
    print(f"\nSending request with Method 1:")
    print(f"  Signature: {signature1}")
    print(f"  Headers: {headers}")
    
    try:
        # Send the exact same body that we signed
        response = requests.post(
            f"http://localhost:8000{path}",
            data=json_str1,  # Send the exact JSON string we signed
            headers=headers,
            timeout=10
        )
        print(f"  Response status: {response.status_code}")
        print(f"  Response body: {response.text}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == '__main__':
    test_body_comparison() 