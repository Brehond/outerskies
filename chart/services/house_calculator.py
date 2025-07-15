"""
House Calculator Service

This service handles all house calculations and cusps.
Focused responsibility: Calculate houses only.
"""

import logging
import swisseph as swe
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# House system constants (using character codes as per Swiss Ephemeris)
HOUSE_SYSTEMS = {
    "Placidus": b'P',
    "Whole Sign": b'W',
    "Koch": b'K',
    "Equal": b'E',
    "Campanus": b'C',
    "Topocentric": b'T'
}

# House names
HOUSE_NAMES = {
    1: "First House - Ascendant",
    2: "Second House",
    3: "Third House",
    4: "Fourth House - IC",
    5: "Fifth House",
    6: "Sixth House",
    7: "Seventh House - Descendant",
    8: "Eighth House",
    9: "Ninth House",
    10: "Tenth House - MC",
    11: "Eleventh House",
    12: "Twelfth House"
}


class HouseCalculator:
    """
    Focused service for house calculations
    """
    
    def __init__(self, default_system: str = "Placidus"):
        self.house_systems = HOUSE_SYSTEMS.copy()
        self.house_names = HOUSE_NAMES.copy()
        self.default_system = default_system
    
    def calculate_houses(self, jd: float, latitude: float, longitude: float, 
                        house_system: str = None) -> Dict[str, Any]:
        """
        Calculate house cusps for a given time and location

        Args:
            jd: Julian Day
            latitude: Latitude in degrees
            longitude: Longitude in degrees
            house_system: House system to use (defaults to instance default)

        Returns:
            Dictionary with house cusps and information
        """
        if house_system is None:
            house_system = self.default_system
        
        system_code = self.house_systems.get(house_system)
        if system_code is None:
            raise ValueError(f"Unknown house system: {house_system}")
        
        try:
            # Calculate houses using Swiss Ephemeris
            houses = swe.houses(jd, latitude, longitude, system_code)
            
            # Extract cusps (houses[0] contains cusps 1-12)
            cusps = houses[0]
            
            # Extract Ascendant and MC
            ascendant = houses[1][0]  # Ascendant
            mc = houses[1][1]  # Midheaven
            
            # Convert cusps to sign and degree format
            house_data = {
                "system": house_system,
                "ascendant": self._convert_to_sign_degree(ascendant),
                "mc": self._convert_to_sign_degree(mc),
                "cusps": {}
            }
            
            # Process each house cusp
            for i, cusp in enumerate(cusps[:12], 1):  # First 12 houses
                house_data["cusps"][i] = self._convert_to_sign_degree(cusp)
            
            return house_data
            
        except Exception as e:
            logger.error(f"Error calculating houses: {e}")
            raise
    
    def _convert_to_sign_degree(self, longitude: float) -> Dict[str, Any]:
        """
        Convert ecliptic longitude to sign and degree format

        Args:
            longitude: Ecliptic longitude in degrees

        Returns:
            Dictionary with sign and degree information
        """
        sign_index = int(longitude // 30) % 12
        deg_in_sign = longitude % 30
        
        sign_names = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        
        return {
            "absolute_degree": longitude,
            "sign": sign_names[sign_index],
            "degree_in_sign": deg_in_sign
        }
    
    def find_planet_house(self, planet_longitude: float, house_cusps: Dict[int, Dict[str, Any]]) -> int:
        """
        Find which house a planet is in

        Args:
            planet_longitude: Planet's ecliptic longitude
            house_cusps: Dictionary of house cusps

        Returns:
            House number (1-12)
        """
        # Handle case where planet is between 12th house cusp and 1st house cusp
        cusp1 = house_cusps[1]["absolute_degree"]
        cusp12 = house_cusps[12]["absolute_degree"]
        
        # Check if planet is in 1st house (between 12th and 1st cusps)
        if cusp12 > cusp1:  # Normal case
            if planet_longitude >= cusp12 or planet_longitude < cusp1:
                return 1
        else:  # 12th house cusp crosses 0° Aries
            if planet_longitude >= cusp12 and planet_longitude < cusp1:
                return 1
        
        # Check other houses
        for house_num in range(1, 12):
            cusp_current = house_cusps[house_num]["absolute_degree"]
            cusp_next = house_cusps[house_num + 1]["absolute_degree"]
            
            if cusp_current <= cusp_next:  # Normal case
                if cusp_current <= planet_longitude < cusp_next:
                    return house_num + 1
            else:  # House cusp crosses 0° Aries
                if planet_longitude >= cusp_current or planet_longitude < cusp_next:
                    return house_num + 1
        
        # Fallback to 12th house
        return 12
    
    def assign_planets_to_houses(self, planet_positions: Dict[str, Dict[str, Any]], 
                                house_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Assign planets to their respective houses

        Args:
            planet_positions: Dictionary of planet positions
            house_data: House calculation data

        Returns:
            Dictionary of planets with house assignments
        """
        house_cusps = house_data["cusps"]
        planets_with_houses = {}
        
        for planet, position in planet_positions.items():
            planet_longitude = position.get("absolute_degree", 0)
            house_number = self.find_planet_house(planet_longitude, house_cusps)
            
            # Create new position data with house information
            planet_data = position.copy()
            planet_data["house"] = house_number
            planet_data["house_name"] = self.house_names.get(house_number, f"House {house_number}")
            
            planets_with_houses[planet] = planet_data
        
        return planets_with_houses
    
    def get_house_summary(self, house_data: Dict[str, Any]) -> str:
        """
        Generate a summary of house positions

        Args:
            house_data: House calculation data

        Returns:
            Summary string
        """
        asc = house_data["ascendant"]
        mc = house_data["mc"]
        
        summary = f"Ascendant: {asc['sign']} {asc['degree_in_sign']:.1f}°"
        summary += f" | MC: {mc['sign']} {mc['degree_in_sign']:.1f}°"
        summary += f" | System: {house_data['system']}"
        
        return summary
    
    def get_house_rulers(self, house_data: Dict[str, Any]) -> Dict[int, str]:
        """
        Get the rulers of each house based on traditional rulership

        Args:
            house_data: House calculation data

        Returns:
            Dictionary mapping house numbers to their rulers
        """
        # Traditional rulerships
        sign_rulers = {
            "Aries": "Mars",
            "Taurus": "Venus",
            "Gemini": "Mercury",
            "Cancer": "Moon",
            "Leo": "Sun",
            "Virgo": "Mercury",
            "Libra": "Venus",
            "Scorpio": "Mars",
            "Sagittarius": "Jupiter",
            "Capricorn": "Saturn",
            "Aquarius": "Saturn",
            "Pisces": "Jupiter"
        }
        
        house_rulers = {}
        cusps = house_data["cusps"]
        
        for house_num, cusp_data in cusps.items():
            sign = cusp_data["sign"]
            ruler = sign_rulers.get(sign, "Unknown")
            house_rulers[house_num] = ruler
        
        return house_rulers
    
    def validate_house_system(self, house_system: str) -> bool:
        """
        Validate if a house system is supported

        Args:
            house_system: House system name

        Returns:
            True if valid, False otherwise
        """
        return house_system in self.house_systems
    
    def get_available_house_systems(self) -> List[str]:
        """
        Get list of available house systems

        Returns:
            List of house system names
        """
        return list(self.house_systems.keys())
    
    def calculate_house_strengths(self, house_data: Dict[str, Any], 
                                planet_positions: Dict[str, Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        """
        Calculate strength/activity of each house based on planets in them

        Args:
            house_data: House calculation data
            planet_positions: Planet positions with house assignments

        Returns:
            Dictionary mapping house numbers to strength information
        """
        house_strengths = {}
        
        # Initialize all houses
        for house_num in range(1, 13):
            house_strengths[house_num] = {
                "planets": [],
                "planet_count": 0,
                "strength": "empty",
                "description": "No planets"
            }
        
        # Count planets in each house
        for planet, position in planet_positions.items():
            house_num = position.get("house", 1)
            if house_num in house_strengths:
                house_strengths[house_num]["planets"].append(planet)
                house_strengths[house_num]["planet_count"] += 1
        
        # Determine house strength
        for house_num, house_info in house_strengths.items():
            planet_count = house_info["planet_count"]
            
            if planet_count == 0:
                house_info["strength"] = "empty"
                house_info["description"] = "No planets"
            elif planet_count == 1:
                house_info["strength"] = "active"
                house_info["description"] = f"1 planet: {', '.join(house_info['planets'])}"
            elif planet_count == 2:
                house_info["strength"] = "strong"
                house_info["description"] = f"2 planets: {', '.join(house_info['planets'])}"
            else:
                house_info["strength"] = "very_strong"
                house_info["description"] = f"{planet_count} planets: {', '.join(house_info['planets'])}"
        
        return house_strengths
    
    def get_intercepted_signs(self, house_data: Dict[str, Any]) -> Dict[int, List[str]]:
        """
        Find intercepted signs (signs that don't appear on any house cusp)

        Args:
            house_data: House calculation data

        Returns:
            Dictionary mapping house numbers to their intercepted signs
        """
        cusps = house_data["cusps"]
        all_signs = [
            "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
            "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
        ]
        
        # Get signs on cusps
        cusp_signs = set()
        for cusp_data in cusps.values():
            cusp_signs.add(cusp_data["sign"])
        
        # Find intercepted signs
        intercepted_signs = set(all_signs) - cusp_signs
        
        # Assign intercepted signs to houses
        intercepted_by_house = {}
        for house_num in range(1, 13):
            intercepted_by_house[house_num] = []
        
        # This is a simplified approach - in practice, you'd need more complex logic
        # to determine which house contains which intercepted sign
        
        return intercepted_by_house 