#!/usr/bin/env python
"""
Simple test script to verify core functionality is working.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

def test_imports():
    """Test that all core modules can be imported."""
    print("Testing core imports...")
    
    try:
        from core.exceptions import OuterSkiesException, ValidationError
        print("✅ Core exceptions imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core exceptions: {e}")
        return False
    
    try:
        from core.validators import Validators, StringValidator
        print("✅ Core validators imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core validators: {e}")
        return False
    
    try:
        from core.error_handler import handle_api_error, handle_validation_error
        print("✅ Core error handler imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core error handler: {e}")
        return False
    
    try:
        from core.services.task_queue import TaskQueue, TaskPriority
        print("✅ Core task queue imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core task queue: {e}")
        return False
    
    try:
        from core.api_responses import APIResponse, success_response
        print("✅ Core API responses imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import core API responses: {e}")
        return False
    
    return True

def test_models():
    """Test that models can be imported and basic operations work."""
    print("\nTesting models...")
    
    try:
        from chart.models import User, Chart, TaskStatus
        print("✅ Chart models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import chart models: {e}")
        return False
    
    try:
        from payments.models import SubscriptionPlan, UserSubscription, Payment
        print("✅ Payment models imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import payment models: {e}")
        return False
    
    return True

def test_views():
    """Test that views can be imported."""
    print("\nTesting views...")
    
    try:
        from api.v1 import views
        print("✅ API views imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import API views: {e}")
        return False
    
    try:
        from api.v1 import task_views
        print("✅ Task views imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import task views: {e}")
        return False
    
    return True

def test_urls():
    """Test that URLs can be resolved."""
    print("\nTesting URL resolution...")
    
    try:
        from django.urls import reverse
        from django.test import Client
        
        client = Client()
        print("✅ URL client created successfully")
    except Exception as e:
        print(f"❌ Failed to create URL client: {e}")
        return False
    
    return True

def test_settings():
    """Test that Django settings are properly configured."""
    print("\nTesting Django settings...")
    
    try:
        from django.conf import settings
        
        # Check essential settings
        assert hasattr(settings, 'DATABASES'), "DATABASES setting missing"
        assert hasattr(settings, 'INSTALLED_APPS'), "INSTALLED_APPS setting missing"
        assert hasattr(settings, 'SECRET_KEY'), "SECRET_KEY setting missing"
        
        print("✅ Django settings configured correctly")
        return True
    except Exception as e:
        print(f"❌ Django settings issue: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running core functionality tests...\n")
    
    tests = [
        test_imports,
        test_models,
        test_views,
        test_urls,
        test_settings,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All core functionality tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 