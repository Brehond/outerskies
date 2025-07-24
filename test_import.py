#!/usr/bin/env python3
"""
Simple test script to verify imports work correctly
"""

import os
import sys

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

try:
    import django
    django.setup()
    print("✅ Django setup successful")
    
    # Test background processor import
    from chart.services.background_processor import background_processor
    print("✅ Background processor imported successfully")
    
    # Test security service import
    from api.services.security_service import SecurityService
    print("✅ Security service imported successfully")
    
    # Test advanced security import
    from api.security.advanced_security import AdvancedSecuritySystem
    print("✅ Advanced security system imported successfully")
    
    # Test API standardizer import
    from api.services.api_standardizer import APIStandardizer
    print("✅ API standardizer imported successfully")
    
    # Test performance monitor import
    from api.services.performance_monitor import PerformanceMonitor
    print("✅ Performance monitor imported successfully")
    
    print("\n🎉 All Phase 1, 2, and 3 components imported successfully!")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1) 