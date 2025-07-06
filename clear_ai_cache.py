#!/usr/bin/env python
"""
Script to clear the AI interpretation cache to force regeneration of 
planet interpretations with correct house positions.
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

def clear_ai_cache():
    """Clear AI interpretation cache to force regeneration"""
    try:
        # Clear all cache keys that start with 'ai_interp'
        # This will clear all AI interpretation cache entries
        cache.clear()
        print("✅ All caches cleared successfully!")
        print("Next chart generation will regenerate all interpretations with correct house positions.")
        
    except Exception as e:
        print(f"❌ Error clearing AI cache: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧹 Clearing AI interpretation cache...")
    clear_ai_cache() 