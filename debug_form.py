#!/usr/bin/env python
"""
Debug script to test form validation directly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from chart.forms import UserRegistrationForm

def test_form_validation():
    """Test form validation directly"""
    data = {
        'username': 'astrotest',
        'email': 'astro@example.com',
        'password1': 'Testpass123!',
        'password2': 'Wrongpass!',
        'agree_to_terms': True,
        'timezone': 'UTC',
    }
    
    form = UserRegistrationForm(data=data)
    is_valid = form.is_valid()
    
    print(f"Form is valid: {is_valid}")
    
    if not is_valid:
        print("\nForm errors:")
        print("="*60)
        for field, errors in form.errors.items():
            print(f"{field}: {errors}")
        print("="*60)
        
        # Check specifically for password2 errors
        if 'password2' in form.errors:
            print(f"\nPassword2 errors: {form.errors['password2']}")
            
            # Check if the error message contains our expected text
            error_text = str(form.errors['password2'])
            print(f"Error text: '{error_text}'")
            
            if "The two password fields didn't match" in error_text:
                print("✓ Found expected error message")
            else:
                print("✗ Expected error message not found")
                print(f"Looking for: 'The two password fields didn't match'")
                print(f"Found: '{error_text}'")

if __name__ == "__main__":
    test_form_validation() 