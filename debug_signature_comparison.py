#!/usr/bin/env python3
"""
Debug script to compare client and server signature generation.
"""

import hmac
import hashlib
import base64
import json
import time

# Test data
API_SECRET = 'test-api-secret-for-testing'
test_data = {
    "date": "1990-01-01",
    "time": "12:00",
    "latitude": 45.5,
    "longitude": -64.3,
    "timezone_str": "America/Halifax",
    "zodiac_type": "tropical",
    "house_system": "placidus"
}

# Test parameters
method = "POST"
path = "/api/v1/background-charts/calculate_ephemeris/"
query_string = ""
timestamp = "1750809574"
nonce = "jzjwreq7ql5s"

def client_signature_generation():
    """Simulate client signature generation."""
    print("=== CLIENT SIGNATURE GENERATION ===")
    
    # Client uses json.dumps with separators
    body_bytes = json.dumps(test_data, separators=(",", ":")).encode('utf-8')
    body_b64 = base64.b64encode(body_bytes).decode('utf-8')
    
    print(f"JSON data: {json.dumps(test_data, separators=(',', ':'))}")
    print(f"Body bytes: {body_bytes}")
    print(f"Body base64: {body_b64}")
    
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body_b64}'
    print(f"Signature string: {repr(signature_string)}")
    
    signature = hmac.new(
        API_SECRET.encode(),
        signature_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Client signature: {signature}")
    return signature, body_b64

def server_signature_generation():
    """Simulate server signature generation."""
    print("\n=== SERVER SIGNATURE GENERATION ===")
    
    # Server receives the request body as it was sent
    # Let's try different ways the server might receive it
    
    # Method 1: Standard JSON with spaces
    body1 = json.dumps(test_data).encode('utf-8')
    body_b64_1 = base64.b64encode(body1).decode('utf-8')
    
    print(f"Method 1 - Standard JSON:")
    print(f"JSON data: {json.dumps(test_data)}")
    print(f"Body bytes: {body1}")
    print(f"Body base64: {body_b64_1}")
    
    signature_string1 = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body_b64_1}'
    signature1 = hmac.new(
        API_SECRET.encode(),
        signature_string1.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Signature 1: {signature1}")
    
    # Method 2: Compact JSON (like client)
    body2 = json.dumps(test_data, separators=(",", ":")).encode('utf-8')
    body_b64_2 = base64.b64encode(body2).decode('utf-8')
    
    print(f"\nMethod 2 - Compact JSON:")
    print(f"JSON data: {json.dumps(test_data, separators=(',', ':'))}")
    print(f"Body bytes: {body2}")
    print(f"Body base64: {body_b64_2}")
    
    signature_string2 = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body_b64_2}'
    signature2 = hmac.new(
        API_SECRET.encode(),
        signature_string2.encode(),
        hashlib.sha256
    ).hexdigest()
    
    print(f"Signature 2: {signature2}")
    
    return signature1, signature2, body_b64_1, body_b64_2

def main():
    print("DEBUGGING SIGNATURE MISMATCH")
    print("=" * 50)
    
    client_sig, client_body = client_signature_generation()
    server_sig1, server_sig2, server_body1, server_body2 = server_signature_generation()
    
    print("\n=== COMPARISON ===")
    print(f"Client signature: {client_sig}")
    print(f"Server signature (standard): {server_sig1}")
    print(f"Server signature (compact): {server_sig2}")
    
    print(f"\nClient body base64: {client_body}")
    print(f"Server body base64 (standard): {server_body1}")
    print(f"Server body base64 (compact): {server_body2}")
    
    print(f"\nClient vs Server (standard): {'MATCH' if client_sig == server_sig1 else 'MISMATCH'}")
    print(f"Client vs Server (compact): {'MATCH' if client_sig == server_sig2 else 'MISMATCH'}")
    
    # Check what the actual server received from the logs
    print(f"\n=== FROM SERVER LOGS ===")
    print("Expected signature: 903585f810995fa9ead27d919f2fff9e64feae0c01f67303bb0c776473102418")
    print("Received signature: 20c873ea1869a32c44556ddf56518c1a2d78d75b2b8ad800a37647eb07f4ea5d")
    print("Client signature: 20c873ea1869a32c44556ddf56518c1a2d78d75b2b8ad800a37647eb07f4ea5d")
    
    if client_sig == "20c873ea1869a32c44556ddf56518c1a2d78d75b2b8ad800a37647eb07f4ea5d":
        print("✅ Client signature matches received signature")
    else:
        print("❌ Client signature does NOT match received signature")
    
    if server_sig1 == "903585f810995fa9ead27d919f2fff9e64feae0c01f67303bb0c776473102418":
        print("✅ Server signature (standard) matches expected signature")
    elif server_sig2 == "903585f810995fa9ead27d919f2fff9e64feae0c01f67303bb0c776473102418":
        print("✅ Server signature (compact) matches expected signature")
    else:
        print("❌ Neither server signature matches expected signature")

if __name__ == '__main__':
    main() 