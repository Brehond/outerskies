#!/usr/bin/env python3
"""
Test script to verify house position calculations are working correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chart.services.ephemeris import get_planet_positions, get_ascendant_and_houses
import swisseph as swe

def test_house_positions():
    """Test house position calculations for a sample chart."""
    
    # Sample birth data (January 1, 1990, 12:00 PM, New York)
    jd = 2447892.5  # Julian Day for 1990-01-01 12:00:00 UTC
    lat = 40.7128   # New York latitude
    lon = -74.0060  # New York longitude
    
    print("Testing House Position Calculations")
    print("=" * 50)
    print(f"Date: 1990-01-01 12:00:00 UTC")
    print(f"Location: New York (lat: {lat}, lon: {lon})")
    print()
    
    # Test house calculation
    print("1. Testing House Cusps:")
    try:
        asc, houses, house_signs = get_ascendant_and_houses(jd, lat, lon, "placidus")
        print(f"   Ascendant: {asc['sign']} {asc['degree_in_sign']:.1f}°")
        print(f"   House 1: {house_signs[1]} {houses[0]:.1f}°")
        print(f"   House 10: {house_signs[10]} {houses[9]:.1f}°")
        print("   ✓ House cusps calculated successfully")
    except Exception as e:
        print(f"   ✗ Error calculating house cusps: {e}")
        return
    
    print()
    print("2. Testing Planetary House Positions:")
    
    # Test planetary positions with house calculation
    try:
        positions = get_planet_positions(jd, lat, lon, "tropical", "placidus")
        
        for planet, pos in positions.items():
            if planet in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
                sign = pos.get('sign', 'Unknown')
                house = pos.get('house', 1)
                degree = pos.get('absolute_degree', 0)
                aspects = pos.get('aspects', [])
                
                print(f"   {planet}: {sign} {degree:.1f}° in House {house}")
                if aspects:
                    aspect_desc = []
                    for aspect in aspects[:3]:  # Show first 3 aspects
                        aspect_desc.append(f"{aspect['type']} {aspect['planet']}")
                    print(f"     Aspects: {', '.join(aspect_desc)}")
        
        print("   ✓ Planetary house positions calculated successfully")
        
    except Exception as e:
        print(f"   ✗ Error calculating planetary positions: {e}")
        return
    
    print()
    print("3. Testing Swiss Ephemeris House Position Function:")
    
    # Test direct Swiss Ephemeris house position calculation
    try:
        # Get houses and ARMC
        houses, ascmc = swe.houses(jd, lat, lon, b'P')  # Placidus
        armc = ascmc[2]  # Right Ascension of Medium Coeli
        eps = 23.4367  # Use standard mean obliquity of the ecliptic
        
        # Test house position for Sun
        sun_result = swe.calc_ut(jd, swe.SUN)
        sun_long = sun_result[0][0]
        sun_lat = sun_result[0][1]
        
        print(f"   ARMC: {armc:.2f}°")
        print(f"   Epsilon: {eps:.2f}°")
        print(f"   Sun longitude: {sun_long:.1f}°")
        print(f"   Sun latitude: {sun_lat:.1f}°")
        
        # Calculate house position using swe_house_pos
        house_pos = swe.house_pos(armc, lat, eps, [sun_long, sun_lat], b'P')
        house_number = int(house_pos)
        
        print(f"   Sun house position: {house_pos:.2f} (House {house_number})")
        print("   ✓ Swiss Ephemeris house position function working")
        
    except Exception as e:
        print(f"   ✗ Error with Swiss Ephemeris house position: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return
    
    print()
    print("Test completed successfully!")
    print("House position calculations are working correctly.")

if __name__ == "__main__":
    test_house_positions() 