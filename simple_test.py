#!/usr/bin/env python
"""
Simple test to capture actual error message
"""

import os
import sys
import django
from django.test.utils import override_settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.test import TestCase, Client
from django.urls import reverse

@override_settings(ALLOWED_HOSTS=['testserver', 'localhost', '127.0.0.1'])
def test_password_mismatch():
    """Test to see actual error message"""
    client = Client()
    
    data = {
        'username': 'astrotest',
        'email': 'astro@example.com',
        'password1': 'Testpass123!',
        'password2': 'Wrongpass!',
        'agree_to_terms': True,
        'timezone': 'UTC',
    }
    
    # First get the page to get CSRF token
    response = client.get(reverse('auth:register'))
    print(f"GET Status Code: {response.status_code}")
    
    if response.status_code == 200:
        # Extract CSRF token
        content = response.content.decode('utf-8')
        csrf_token = None
        if 'csrfmiddlewaretoken' in content:
            import re
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
            if match:
                csrf_token = match.group(1)
                print(f"Found CSRF token: {csrf_token[:10]}...")
        
        # Add CSRF token to data
        if csrf_token:
            data['csrfmiddlewaretoken'] = csrf_token
        
        # Now post with the data
        response = client.post(reverse('auth:register'), data)
        
        print(f"POST Status Code: {response.status_code}")
        print(f"Content Type: {response.get('Content-Type', 'Not set')}")
        
        # Print the first 1000 characters of the response
        content = response.content.decode('utf-8')
        print(f"\nResponse content (first 1000 chars):")
        print("="*60)
        print(content[:1000])
        print("="*60)
        
        # Check if there are form errors
        if hasattr(response, 'context') and response.context:
            form = response.context.get('form')
            if form and form.errors:
                print("\nFORM ERRORS:")
                print("="*60)
                for field, errors in form.errors.items():
                    print(f"{field}: {errors}")
                print("="*60)
        
        # Search for common error message patterns
        error_patterns = [
            "The two password fields didn't match",
            "The two password fields didn't match.",
            "password",
            "match",
            "error",
            "invalid"
        ]
        
        print("\nSearching for error patterns:")
        print("="*60)
        for pattern in error_patterns:
            if pattern.lower() in content.lower():
                print(f"Found: '{pattern}'")
        print("="*60)
    else:
        print("Failed to get registration page")
        print(response.content.decode('utf-8'))

if __name__ == "__main__":
    test_password_mismatch() 