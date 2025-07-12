#!/usr/bin/env python
"""
Debug script to capture registration form response
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.test import Client
from django.urls import reverse


def debug_registration_response():
    """Debug the registration form response"""
    client = Client()

    # First get the registration page to get CSRF token
    response = client.get(reverse('auth:register'))
    print(f"GET Status Code: {response.status_code}")

    if response.status_code == 200:
        # Extract CSRF token from the response
        csrf_token = None
        content = response.content.decode('utf-8')
        if 'csrfmiddlewaretoken' in content:
            # Find the CSRF token in the HTML
            import re
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', content)
            if match:
                csrf_token = match.group(1)
                print(f"Found CSRF token: {csrf_token[:10]}...")

        # Test data with mismatched passwords
        data = {
            'username': 'astrotest',
            'email': 'astro@example.com',
            'password1': 'Testpass123!',
            'password2': 'Wrongpass!',
            'agree_to_terms': True,
            'timezone': 'UTC',
        }

        # Add CSRF token if found
        if csrf_token:
            data['csrfmiddlewaretoken'] = csrf_token

        print(f"\nPOST data: {data}")

        # Make the POST request
        response = client.post(reverse('auth:register'), data)

        print(f"POST Status Code: {response.status_code}")
        print(f"Content Type: {response.get('Content-Type', 'Not set')}")
        print("\n" + "=" * 60)
        print("RESPONSE CONTENT:")
        print("=" * 60)
        print(response.content.decode('utf-8'))
        print("=" * 60)

        # Check if there are any form errors
        if hasattr(response, 'context') and response.context:
            form = response.context.get('form')
            if form and form.errors:
                print("\nFORM ERRORS:")
                print("=" * 60)
                for field, errors in form.errors.items():
                    print(f"{field}: {errors}")
                print("=" * 60)
    else:
        print("Failed to get registration page")
        print(response.content.decode('utf-8'))


if __name__ == "__main__":
    debug_registration_response() 