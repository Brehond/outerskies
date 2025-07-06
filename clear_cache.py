#!/usr/bin/env python
"""
Script to clear the ephemeris cache to force recalculation of chart data
with correct house positions.
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
import logging

logger = logging.getLogger(__name__)

def clear_caches():
    """Clear all caches to force recalculation"""
    try:
        # Clear all Django cache
        cache.clear()
        print("✅ All caches cleared successfully!")
        print("Next chart generation will use fresh calculations with correct house positions.")
        
    except Exception as e:
        print(f"❌ Error clearing caches: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧹 Clearing Outer Skies caches...")
    clear_caches() 