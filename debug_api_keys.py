#!/usr/bin/env python3
"""
Debug script to check API key configuration across the system.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.conf import settings

def check_api_keys():
    """Check API key configuration."""
    print("=== API Key Configuration Debug ===")
    
    # Check environment variables
    env_api_key = os.getenv('API_KEY')
    env_api_secret = os.getenv('API_SECRET')
    
    print(f"Environment API_KEY: {env_api_key}")
    print(f"Environment API_SECRET: {env_api_secret[:20]}..." if env_api_secret else "Environment API_SECRET: None")
    
    # Check Django settings
    print(f"Django settings API_KEY: {settings.API_KEY}")
    print(f"Django settings API_SECRET: {settings.API_SECRET[:20]}..." if settings.API_SECRET else "Django settings API_SECRET: None")
    
    # Check if they match
    key_match = env_api_key == settings.API_KEY
    secret_match = env_api_secret == settings.API_SECRET
    
    print(f"\nAPI_KEY match: {'✅' if key_match else '❌'}")
    print(f"API_SECRET match: {'✅' if secret_match else '❌'}")
    
    # Test signature generation
    import hmac
    import hashlib
    import base64
    import time
    
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    method = 'POST'
    path = '/api/v1/background-charts/calculate_ephemeris/'
    query_string = ''
    timestamp = str(int(time.time()))
    nonce = 'testnonce123'
    body = base64.b64encode(str(test_data).encode()).decode()
    
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
    
    print(f"\n=== Signature Test ===")
    print(f"Method: {method}")
    print(f"Path: {path}")
    print(f"Timestamp: {timestamp}")
    print(f"Nonce: {nonce}")
    print(f"Body: {body[:50]}...")
    print(f"Signature string: {repr(signature_string)}")
    
    # Generate signature with environment secret
    if env_api_secret:
        env_signature = hmac.new(
            env_api_secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        print(f"Environment signature: {env_signature}")
    
    # Generate signature with settings secret
    if settings.API_SECRET:
        settings_signature = hmac.new(
            settings.API_SECRET.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()
        print(f"Settings signature: {settings_signature}")
    
    if env_api_secret and settings.API_SECRET:
        signature_match = env_signature == settings_signature
        print(f"Signature match: {'✅' if signature_match else '❌'}")

if __name__ == '__main__':
    check_api_keys() 