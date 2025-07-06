#!/usr/bin/env python3
"""
Debug script for house calculation issues.
"""

import swisseph as swe
import datetime

def test_house_calculation():
    """Test house calculation step by step."""
    print("Testing house calculation...")
    
    # Test parameters from the error
    date = "1993-07-22"
    time = "00:40"
    lat = 45.5
    lon = -64.3
    house_system = "whole_sign"
    
    try:
        # Convert to Julian Day
        dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        jd = swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)
        print(f"Julian Day: {jd}")
        
        # Map house system
        hs_map = {
            'placidus': 'P',
            'whole_sign': 'W',
        }
        hs_code = hs_map.get(house_system, 'P')
        print(f"House system code: {hs_code}")
        
        # Calculate houses
        print(f"Calculating houses with: jd={jd}, lat={lat}, lon={lon}, hs={hs_code}")
        houses, ascmc = swe.houses(jd, lat, lon, hs_code.encode('utf-8'))
        
        print(f"Houses array: {houses}")
        print(f"Houses array length: {len(houses)}")
        print(f"ASCMC array: {ascmc}")
        
        if len(houses) >= 13:
            print(f"House 1: {houses[1]}")
            print(f"House 10 (MC): {houses[10]}")
            print("✅ House calculation successful")
        else:
            print("❌ Houses array too short")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_house_calculation() 