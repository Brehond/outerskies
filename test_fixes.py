#!/usr/bin/env python3
"""
Test script to verify the fixes for the chart generation errors.
"""

import sys
import os
import django

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from chart.services.ephemeris import get_chart_data, get_ascendant_and_houses
from chart.views import generate_master_interpretation_with_caching
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_house_calculation():
    """Test house calculation for the specific longitude that was causing issues."""
    print("Testing house calculation...")
    
    try:
        # Test with the specific date/time that was causing issues
        date = "1993-07-22"
        time = "00:40"
        lat = 45.5
        lon = -64.3
        house_system = "whole_sign"
        
        # Test the house calculation directly
        from chart.services.ephemeris import get_julian_day
        jd = get_julian_day(date, time)
        asc, houses, house_signs = get_ascendant_and_houses(jd, lat, lon, house_system)
        
        print(f"✅ House calculation successful")
        print(f"   Houses array length: {len(houses)}")
        print(f"   House 10 (MC): {houses[10] if len(houses) > 10 else 'N/A'}")
        print(f"   House signs: {house_signs}")
        
        return True
        
    except Exception as e:
        print(f"❌ House calculation failed: {e}")
        return False

def test_chart_data_structure():
    """Test the complete chart data structure."""
    print("\nTesting chart data structure...")
    
    try:
        # Test with the specific date/time that was causing issues
        date = "1993-07-22"
        time = "00:40"
        lat = 45.5
        lon = -64.3
        house_system = "whole_sign"
        
        chart_data = get_chart_data(date, time, lat, lon, "UTC", "tropical", house_system)
        
        print(f"✅ Chart data generation successful")
        print(f"   Has planetary_positions: {'planetary_positions' in chart_data}")
        print(f"   Has house_cusps: {'house_cusps' in chart_data}")
        print(f"   Has house_signs: {'house_signs' in chart_data}")
        print(f"   House cusps length: {len(chart_data.get('house_cusps', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chart data generation failed: {e}")
        return False

def test_master_interpretation():
    """Test the master interpretation generation."""
    print("\nTesting master interpretation generation...")
    
    try:
        # Test with the specific date/time that was causing issues
        date = "1993-07-22"
        time = "00:40"
        lat = 45.5
        lon = -64.3
        house_system = "whole_sign"
        
        chart_data = get_chart_data(date, time, lat, lon, "UTC", "tropical", house_system)
        
        # Test the master interpretation function
        interpretation = generate_master_interpretation_with_caching(
            chart_data,
            date,
            time,
            "Kentville, Canada",
            "gpt-3.5-turbo",
            0.7,
            1000
        )
        
        print(f"✅ Master interpretation generation successful")
        print(f"   Interpretation length: {len(interpretation)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Master interpretation generation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing chart generation fixes...\n")
    
    tests = [
        test_house_calculation,
        test_chart_data_structure,
        test_master_interpretation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main()) 