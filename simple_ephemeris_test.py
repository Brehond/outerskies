#!/usr/bin/env python3
"""
Simple test to check Swiss Ephemeris functionality.
"""

try:
    import swisseph as swe
    print("✅ Swiss Ephemeris imported successfully")
    
    # Test basic functionality
    jd = swe.julday(1990, 1, 1, 12.0)
    print(f"✅ Julian Day calculation: {jd}")
    
    # Test planet calculation
    pos, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_SPEED)
    print(f"✅ Sun position calculation: {pos[0]} degrees")
    
    print("✅ All Swiss Ephemeris tests passed!")
    
except ImportError as e:
    print(f"❌ Swiss Ephemeris import failed: {e}")
except Exception as e:
    print(f"❌ Swiss Ephemeris test failed: {e}")
    import traceback
    traceback.print_exc() 