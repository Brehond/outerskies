"""
Planetary Position Calculator Service

This service handles all planetary position calculations using Swiss Ephemeris.
Focused responsibility: Calculate planetary positions only.
"""

import logging
import swisseph as swe
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Define planet code mapping (Sun=0, Moon=1, etc. as per Swiss Ephemeris)
PLANET_CODES = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]


class PlanetaryCalculator:
    """
    Focused service for planetary position calculations
    """
    
    def __init__(self):
        self.planet_codes = PLANET_CODES
        self.sign_names = SIGN_NAMES
    
    def get_sign_from_longitude(self, longitude: float) -> tuple[str, float]:
        """
        Convert ecliptic longitude to (sign, degree_in_sign)

        Args:
            longitude: Ecliptic longitude in degrees

        Returns:
            Tuple of (sign name, degree within sign)
        """
        sign_index = int(longitude // 30) % 12
        deg_in_sign = longitude % 30
        return self.sign_names[sign_index], deg_in_sign
    
    def calculate_planet_position(self, jd: float, planet_name: str) -> Dict[str, Any]:
        """
        Calculate position for a single planet

        Args:
            jd: Julian Day
            planet_name: Name of the planet

        Returns:
            Dictionary with planet position data
        """
        try:
            planet_code = self.planet_codes.get(planet_name)
            if planet_code is None:
                raise ValueError(f"Unknown planet: {planet_name}")
            
            # Get planet position
            result = swe.calc_ut(jd, planet_code)
            longitude = result[0][0]
            latitude = result[0][1]
            distance = result[0][2]
            
            # Convert to sign and degree
            sign, deg_in_sign = self.get_sign_from_longitude(longitude)
            
            # Check if retrograde
            speed = result[0][3]  # Daily motion
            retrograde = speed < 0
            
            return {
                "absolute_degree": longitude,
                "sign": sign,
                "degree_in_sign": deg_in_sign,
                "latitude": latitude,
                "distance": distance,
                "retrograde": "Retrograde" if retrograde else "",
                "speed": speed
            }
            
        except Exception as e:
            logger.error(f"Error calculating position for {planet_name}: {e}")
            raise
    
    def calculate_all_planetary_positions(self, jd: float) -> Dict[str, Dict[str, Any]]:
        """
        Calculate positions for all planets

        Args:
            jd: Julian Day

        Returns:
            Dictionary mapping planet names to their positions
        """
        positions = {}
        
        for planet_name in self.planet_codes.keys():
            try:
                positions[planet_name] = self.calculate_planet_position(jd, planet_name)
            except Exception as e:
                logger.error(f"Failed to calculate {planet_name}: {e}")
                # Continue with other planets
                continue
        
        return positions
    
    def get_planet_list(self) -> List[str]:
        """
        Get list of available planets

        Returns:
            List of planet names
        """
        return list(self.planet_codes.keys())
    
    def validate_planet_name(self, planet_name: str) -> bool:
        """
        Validate if a planet name is supported

        Args:
            planet_name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        return planet_name in self.planet_codes 