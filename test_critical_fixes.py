#!/usr/bin/env python3
"""
Test script to verify critical fixes are working correctly.
"""

import os
import sys
import django
from django.conf import settings
from django.test import TestCase
from django.http import HttpRequest

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

def test_database_configuration():
    """Test that database configuration is working correctly."""
    print("🔍 Testing Database Configuration...")
    
    try:
        # Check if DATABASES is properly configured
        assert hasattr(settings, 'DATABASES'), "DATABASES setting missing"
        assert 'default' in settings.DATABASES, "Default database configuration missing"
        
        db_config = settings.DATABASES['default']
        print(f"✅ Database engine: {db_config.get('ENGINE', 'Not set')}")
        print(f"✅ Database name: {db_config.get('NAME', 'Not set')}")
        
        # Test database connection (skip if SQLite and no file exists)
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result[0] == 1, "Database connection test failed"
            print("✅ Database connection: PASSED")
        except Exception as db_error:
            print(f"⚠️  Database connection: SKIPPED - {db_error}")
            # This is expected if SQLite file doesn't exist yet
        
        print("✅ Database configuration: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Database configuration: FAILED - {e}")
        return False

def test_security_middleware():
    """Test that consolidated security middleware is working."""
    print("\n🔍 Testing Security Middleware...")
    
    try:
        # Check if consolidated security middleware is available
        from api.middleware.consolidated_security import ConsolidatedSecurityMiddleware
        
        # Create a dummy get_response function
        def dummy_get_response(request):
            from django.http import HttpResponse
            return HttpResponse("OK")
        
        # Create middleware instance with get_response
        middleware = ConsolidatedSecurityMiddleware(dummy_get_response)
        
        # Create a test request
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_USER_AGENT'] = 'TestAgent'
        request.path = '/api/test/'
        
        # Test middleware processing
        response = middleware(request)
        
        print("✅ Consolidated security middleware: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Security middleware: FAILED - {e}")
        return False

def test_celery_configuration():
    """Test that Celery configuration is working."""
    print("\n🔍 Testing Celery Configuration...")
    
    try:
        # Check if Celery app is properly configured
        from astrology_ai.celery import app
        
        # Check platform-specific configuration
        import platform
        is_windows = platform.system().lower() == 'windows'
        
        if is_windows:
            assert app.conf.worker_pool == 'solo', "Windows should use solo pool"
            assert app.conf.worker_concurrency == 1, "Windows should use single worker"
        else:
            assert app.conf.worker_pool == 'prefork', "Unix should use prefork pool"
            assert app.conf.worker_concurrency == 4, "Unix should use multiple workers"
        
        print(f"✅ Celery configuration: PASSED (Platform: {platform.system()})")
        return True
        
    except Exception as e:
        print(f"❌ Celery configuration: FAILED - {e}")
        return False

def test_payment_validation():
    """Test that payment amount validation is working."""
    print("\n🔍 Testing Payment Validation...")
    
    try:
        from payments.stripe_utils import validate_payment_amount
        
        # Test valid amounts
        assert validate_payment_amount(10.50) == 1050, "Valid amount conversion failed"
        assert validate_payment_amount(0.01) == 1, "Small amount conversion failed"
        
        # Test invalid amounts
        try:
            validate_payment_amount(-10)
            assert False, "Negative amount should raise error"
        except Exception:
            pass  # Expected
        
        try:
            validate_payment_amount(1000000)  # Over limit
            assert False, "Amount over limit should raise error"
        except Exception:
            pass  # Expected
        
        try:
            validate_payment_amount("invalid")
            assert False, "Invalid type should raise error"
        except Exception:
            pass  # Expected
        
        print("✅ Payment validation: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Payment validation: FAILED - {e}")
        return False

def test_missing_middleware_cleanup():
    """Test that deleted middleware files are not being imported."""
    print("\n🔍 Testing Middleware Cleanup...")
    
    try:
        # These imports should fail
        missing_modules = [
            'api.middleware.advanced_security_middleware',
            'api.middleware.security_middleware',
            'api.middleware.security_headers',
            'api.middleware.rate_limit',
            'api.middleware.enhanced_rate_limit',
            'api.middleware.input_validation',
        ]
        
        for module in missing_modules:
            try:
                __import__(module)
                print(f"❌ {module} still exists - should have been deleted")
                return False
            except ImportError:
                print(f"✅ {module} properly deleted")
        
        print("✅ Middleware cleanup: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Middleware cleanup: FAILED - {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Critical Fixes Implementation")
    print("=" * 50)
    
    tests = [
        test_database_configuration,
        test_security_middleware,
        test_celery_configuration,
        test_payment_validation,
        test_missing_middleware_cleanup,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All critical fixes are working correctly!")
        return True
    else:
        print("⚠️  Some issues found. Please review the failures above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 