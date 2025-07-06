#!/usr/bin/env python3
"""
Comprehensive test script that captures all output to a text file and provides detailed analysis.
"""

import requests
import json
import hmac
import hashlib
import base64
import random
import string
import time
import os
import sys
from datetime import datetime

# Test configuration
API_SECRET = 'test-api-secret-for-testing'
API_KEY = 'test-api-key-for-testing'
BASE_URL = "http://localhost:8000"
LOG_FILE = "test_output.txt"

def log_message(message):
    """Log message to both console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(formatted_message + '\n')

def generate_signature(method, path, query_string, timestamp, nonce, body=''):
    """Generate HMAC signature."""
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
    return hmac.new(
        API_SECRET.encode(),
        signature_string.encode(),
        hashlib.sha256
    ).hexdigest()

def get_signed_headers(method, path, body=None):
    """Generate signed headers for API requests."""
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
    
    headers = {
        'X-Signature': signature,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json',
    }
    
    log_message(f"Generated headers for {method} {path}:")
    log_message(f"  Timestamp: {timestamp}")
    log_message(f"  Nonce: {nonce}")
    log_message(f"  Body base64: {body_b64[:50]}..." if body_b64 else "  Body: empty")
    log_message(f"  Signature: {signature}")
    
    return headers

def analyze_log_file():
    """Analyze the log file for patterns and issues."""
    log_message("\n=== ANALYZING LOG FILE ===")
    
    if not os.path.exists(LOG_FILE):
        log_message("No log file found.")
        return
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count different types of responses
    status_200 = content.count('Status: 200')
    status_400 = content.count('Status: 400')
    status_401 = content.count('Status: 401')
    status_500 = content.count('Status: 500')
    
    log_message(f"Response counts:")
    log_message(f"  200 OK: {status_200}")
    log_message(f"  400 Bad Request: {status_400}")
    log_message(f"  401 Unauthorized: {status_401}")
    log_message(f"  500 Server Error: {status_500}")
    
    # Look for specific error patterns
    if 'Invalid request signature' in content:
        log_message("⚠️  SIGNATURE ISSUE DETECTED")
        log_message("   - Multiple 'Invalid request signature' errors found")
        log_message("   - This suggests a mismatch between client and server signature generation")
    
    if 'Invalid request nonce' in content:
        log_message("⚠️  NONCE ISSUE DETECTED")
        log_message("   - Multiple 'Invalid request nonce' errors found")
        log_message("   - This suggests nonce validation problems")
    
    if 'Authentication credentials were not provided' in content:
        log_message("⚠️  AUTHENTICATION ISSUE DETECTED")
        log_message("   - Missing or invalid API key")
    
    if 'Connection' in content and 'error' in content.lower():
        log_message("⚠️  CONNECTION ISSUE DETECTED")
        log_message("   - Server connection problems detected")
    
    # Look for successful patterns
    if '✅ PASS' in content:
        log_message("✅ SUCCESS PATTERNS FOUND")
        log_message("   - Some tests are passing successfully")

def run_endpoint_test(name, method, path, data=None, expected_status=[200, 202]):
    """Test a single endpoint and log detailed results."""
    log_message(f"\n=== TESTING {name.upper()} ===")
    log_message(f"Method: {method}")
    log_message(f"Path: {path}")
    if data:
        log_message(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        # Generate headers
        if method == 'GET':
            headers = get_signed_headers(method, path)
            response = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=10)
        else:
            headers = get_signed_headers(method, path, data)
            # Send the exact same JSON that was used for signature generation
            import json as _json
            json_body = _json.dumps(data, separators=(",", ":"))
            response = requests.post(f"{BASE_URL}{path}", data=json_body, headers=headers, timeout=10)
        
        log_message(f"Response Status: {response.status_code}")
        log_message(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            log_message(f"Response Body: {json.dumps(response_json, indent=2)}")
        except:
            log_message(f"Response Body: {response.text}")
        
        if response.status_code in expected_status:
            log_message(f"✅ {name} TEST PASSED")
            return True
        else:
            log_message(f"❌ {name} TEST FAILED")
            return False
            
    except requests.exceptions.ConnectionError as e:
        log_message(f"❌ CONNECTION ERROR: {e}")
        return False
    except requests.exceptions.Timeout as e:
        log_message(f"❌ TIMEOUT ERROR: {e}")
        return False
    except Exception as e:
        log_message(f"❌ UNEXPECTED ERROR: {e}")
        return False

def main():
    """Main test function."""
    # Clear log file
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"=== OUTER SKIES API TEST LOG ===\n")
        f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"API Secret: {API_SECRET}\n")
        f.write(f"API Key: {API_KEY}\n")
        f.write(f"Base URL: {BASE_URL}\n\n")
    
    log_message("=== OUTER SKIES COMPREHENSIVE API TEST ===")
    log_message("Starting comprehensive API testing...")
    
    # Test 1: System Health (Public)
    test1_passed = run_endpoint_test("System Health", "GET", "/api/v1/system/health/")
    
    # Test 2: Celery Health (Signed)
    test2_passed = run_endpoint_test("Celery Health", "GET", "/api/v1/system/celery_health/")
    
    # Test 3: Background Task (Signed)
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    test3_passed = run_endpoint_test("Background Task", "POST", "/api/v1/background-charts/calculate_ephemeris/", test_data)
    
    # Final summary
    log_message("\n=== FINAL TEST SUMMARY ===")
    log_message(f"System Health: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    log_message(f"Celery Health: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    log_message(f"Background Task: {'✅ PASS' if test3_passed else '❌ FAIL'}")
    
    total_passed = sum([test1_passed, test2_passed, test3_passed])
    log_message(f"Total Tests Passed: {total_passed}/3")
    
    if total_passed == 3:
        log_message("🎉 ALL TESTS PASSED! Application is working perfectly without Redis.")
    elif total_passed >= 2:
        log_message("⚠️  MOST TESTS PASSED. Minor issues detected.")
    else:
        log_message("❌ MULTIPLE TESTS FAILED. Significant issues detected.")
    
    # Analyze log file for patterns
    analyze_log_file()
    
    log_message(f"\nDetailed log saved to: {LOG_FILE}")
    log_message("Test completed.")

if __name__ == '__main__':
    main() 