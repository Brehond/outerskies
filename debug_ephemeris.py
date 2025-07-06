#!/usr/bin/env python3
"""
Debug script to test ephemeris functionality and identify the source of errors.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from chart.services.ephemeris import get_julian_day, get_planet_positions, get_ascendant_and_houses

def test_ephemeris_functions():
    """Test ephemeris functions to identify the source of errors."""
    print("=== Ephemeris Function Debug ===")
    
    try:
        # Test 1: Julian Day calculation
        print("1. Testing Julian Day calculation...")
        jd = get_julian_day("1990-01-01", "12:00")
        print(f"   ✅ Julian Day: {jd}")
        
        # Test 2: Planet positions
        print("2. Testing planet positions...")
        positions = get_planet_positions(jd, 45.5, -64.3, zodiac_type='tropical')
        print(f"   ✅ Planet positions calculated for {len(positions)} planets")
        
        # Test 3: Ascendant and houses
        print("3. Testing ascendant and houses...")
        asc, houses, house_signs = get_ascendant_and_houses(jd, 45.5, -64.3, house_system='placidus')
        print(f"   ✅ Ascendant: {asc}")
        print(f"   ✅ Houses: {len(houses)} house cusps")
        print(f"   ✅ House signs: {len(house_signs)} house signs")
        
        # Test 4: Check for None values in positions
        print("4. Checking for None values in planet positions...")
        for planet, pos in positions.items():
            if pos is None:
                print(f"   ❌ {planet} position is None")
            else:
                print(f"   ✅ {planet}: {pos.get('sign', 'N/A')} {pos.get('degree', 'N/A')}°")
        
        # Test 5: Check specific planet data structure
        print("5. Checking planet data structure...")
        sun_pos = positions.get('Sun')
        if sun_pos:
            print(f"   ✅ Sun position structure: {list(sun_pos.keys())}")
            print(f"   ✅ Sun absolute degree: {sun_pos.get('absolute_degree')}")
            print(f"   ✅ Sun sign: {sun_pos.get('sign')}")
            print(f"   ✅ Sun degree: {sun_pos.get('degree')}")
        else:
            print("   ❌ Sun position is None")
        
        print("✅ All ephemeris tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Ephemeris test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_task_parameters():
    """Test the exact parameters that the task is receiving."""
    print("\n=== Task Parameters Test ===")
    
    test_data = {
        "date": "1990-01-01",
        "time": "12:00",
        "latitude": 45.5,
        "longitude": -64.3,
        "timezone_str": "America/Halifax",
        "zodiac_type": "tropical",
        "house_system": "placidus"
    }
    
    print(f"Test data: {test_data}")
    
    try:
        # Convert to UTC (this is what the task does)
        from chart.views import local_to_utc
        utc_date, utc_time = local_to_utc(
            test_data['date'],
            test_data['time'],
            test_data['timezone_str']
        )
        
        print(f"UTC conversion: {utc_date}, {utc_time}")
        
        # Prepare task parameters (exactly like the task)
        ephemeris_params = {
            'utc_date': utc_date,
            'utc_time': utc_time,
            'latitude': float(test_data['latitude']),
            'longitude': float(test_data['longitude']),
            'zodiac_type': test_data['zodiac_type'],
            'house_system': test_data['house_system']
        }
        
        print(f"Task parameters: {ephemeris_params}")
        
        # Test the ephemeris calculation with these exact parameters
        jd = get_julian_day(ephemeris_params['utc_date'], ephemeris_params['utc_time'])
        positions = get_planet_positions(jd, ephemeris_params['latitude'], ephemeris_params['longitude'], zodiac_type=ephemeris_params['zodiac_type'])
        asc, houses, house_signs = get_ascendant_and_houses(jd, ephemeris_params['latitude'], ephemeris_params['longitude'], house_system=ephemeris_params['house_system'])
        
        print(f"✅ Ephemeris calculation successful with task parameters")
        print(f"   Julian Day: {jd}")
        print(f"   Planets: {len(positions)}")
        print(f"   Ascendant: {asc}")
        print(f"   Houses: {len(houses)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Task parameter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Starting ephemeris debug...")
    
    # Test basic ephemeris functions
    basic_test = test_ephemeris_functions()
    
    # Test task parameters
    task_test = test_task_parameters()
    
    if basic_test and task_test:
        print("\n✅ All tests passed! Ephemeris functionality is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the error messages above.") 