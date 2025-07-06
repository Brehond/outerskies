#!/usr/bin/env python
"""
Script to clear the Django session cache that stores chart results
with old house positions.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.core.cache import cache
from django.contrib.sessions.models import Session
import logging

logger = logging.getLogger(__name__)

def clear_session_cache():
    """Clear Django session cache and session data"""
    try:
        # Clear all Django cache
        cache.clear()
        print("✅ Django cache cleared")
        
        # Clear all session data from database
        Session.objects.all().delete()
        print("✅ All session data cleared from database")
        
        print("\n🎉 Session cache cleared successfully!")
        print("Next chart generation will create fresh results with correct house positions.")
        
    except Exception as e:
        print(f"❌ Error clearing session cache: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧹 Clearing Django session cache...")
    clear_session_cache() 