"""
Aspect Calculator Service

This service handles all aspect calculations between planets.
Focused responsibility: Calculate aspects only.
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# Define aspect orbs (in degrees)
ASPECT_ORBS = {
    "Conjunction": 10,
    "Opposition": 10,
    "Trine": 10,
    "Square": 8,
    "Sextile": 6,
    "Quincunx": 3
}

# Define major aspects and their angles
MAJOR_ASPECTS = {
    "Conjunction": 0,
    "Opposition": 180,
    "Trine": 120,
    "Square": 90,
    "Sextile": 60,
    "Quincunx": 150
}


class AspectCalculator:
    """
    Focused service for aspect calculations
    """
    
    def __init__(self, default_orb: float = 8.0):
        self.aspect_orbs = ASPECT_ORBS.copy()
        self.major_aspects = MAJOR_ASPECTS.copy()
        self.default_orb = default_orb
    
    def calculate_angular_distance(self, pos1: float, pos2: float) -> float:
        """
        Calculate angular distance between two positions

        Args:
            pos1: First position in degrees
            pos2: Second position in degrees

        Returns:
            Angular distance in degrees
        """
        diff = abs(pos1 - pos2)
        if diff > 180:
            diff = 360 - diff
        return diff
    
    def find_aspects_between_planets(self, pos1: float, pos2: float, 
                                   planet1: str, planet2: str) -> List[Dict[str, Any]]:
        """
        Find all aspects between two planets

        Args:
            pos1: Position of first planet
            pos2: Position of second planet
            planet1: Name of first planet
            planet2: Name of second planet

        Returns:
            List of aspects found
        """
        aspects = []
        distance = self.calculate_angular_distance(pos1, pos2)
        
        for aspect_name, aspect_angle in self.major_aspects.items():
            orb = self.aspect_orbs.get(aspect_name, self.default_orb)
            
            if abs(distance - aspect_angle) <= orb:
                aspects.append({
                    "planet1": planet1,
                    "planet2": planet2,
                    "type": aspect_name,
                    "angle": aspect_angle,
                    "actual_distance": distance,
                    "orb": abs(distance - aspect_angle),
                    "planet1_pos": pos1,
                    "planet2_pos": pos2,
                    "strength": self._calculate_aspect_strength(abs(distance - aspect_angle))
                })
        
        return aspects
    
    def _calculate_aspect_strength(self, orb: float) -> str:
        """
        Calculate aspect strength based on orb

        Args:
            orb: Orb in degrees

        Returns:
            Strength description
        """
        if orb <= 1.0:
            return "exact"
        elif orb <= 3.0:
            return "strong"
        elif orb <= 5.0:
            return "moderate"
        else:
            return "wide"
    
    def calculate_all_aspects(self, positions: Dict[str, Dict[str, Any]], 
                            orb: float = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculate aspects between all planets

        Args:
            positions: Dictionary of planet positions
            orb: Orb to use (overrides default)

        Returns:
            Dictionary mapping planets to their aspects
        """
        if orb is not None:
            self.default_orb = orb
        
        aspects = {}
        
        # Initialize aspects dictionary
        for planet in positions.keys():
            aspects[planet] = []
        
        # Calculate aspects between all planet pairs
        planet_names = list(positions.keys())
        
        for i, planet1 in enumerate(planet_names):
            for planet2 in planet_names[i + 1:]:
                pos1 = positions[planet1].get("absolute_degree", 0)
                pos2 = positions[planet2].get("absolute_degree", 0)
                
                planet_aspects = self.find_aspects_between_planets(
                    pos1, pos2, planet1, planet2
                )
                
                # Add aspects to both planets
                for aspect in planet_aspects:
                    aspects[planet1].append(aspect)
                    aspects[planet2].append(aspect)
        
        return aspects
    
    def find_aspect_patterns(self, aspects: Dict[str, List[Dict[str, Any]]], positions: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Find aspect patterns (grand trine, t-square, etc.)

        Args:
            aspects: Dictionary of aspects by planet
            positions: Dictionary of planet positions (needed for stelliums)

        Returns:
            List of aspect patterns found
        """
        patterns = []
        
        # Find grand trines (three planets in trine)
        grand_trines = self._find_grand_trines(aspects)
        patterns.extend(grand_trines)
        
        # Find t-squares (two squares and one opposition)
        t_squares = self._find_t_squares(aspects)
        patterns.extend(t_squares)
        
        # Find stelliums (three or more planets in same sign)
        if positions:
            stelliums = self._find_stelliums(positions)
            patterns.extend(stelliums)
        
        return patterns
    
    def _find_grand_trines(self, aspects: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Find grand trine patterns

        Args:
            aspects: Dictionary of aspects by planet

        Returns:
            List of grand trine patterns
        """
        grand_trines = []
        planets = list(aspects.keys())
        
        for i, planet1 in enumerate(planets):
            for j, planet2 in enumerate(planets[i + 1:], i + 1):
                for k, planet3 in enumerate(planets[j + 1:], j + 1):
                    # Check if all three planets form trines
                    trine_count = 0
                    for aspect_list in [aspects[planet1], aspects[planet2], aspects[planet3]]:
                        for aspect in aspect_list:
                            if (aspect["type"] == "Trine" and 
                                aspect["planet1"] in [planet1, planet2, planet3] and
                                aspect["planet2"] in [planet1, planet2, planet3]):
                                trine_count += 1
                    
                    if trine_count >= 3:
                        grand_trines.append({
                            "type": "Grand Trine",
                            "planets": [planet1, planet2, planet3],
                            "description": f"Grand trine between {planet1}, {planet2}, and {planet3}"
                        })
        
        return grand_trines
    
    def _find_t_squares(self, aspects: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Find t-square patterns

        Args:
            aspects: Dictionary of aspects by planet

        Returns:
            List of t-square patterns
        """
        t_squares = []
        planets = list(aspects.keys())
        
        for i, planet1 in enumerate(planets):
            for j, planet2 in enumerate(planets[i + 1:], i + 1):
                for k, planet3 in enumerate(planets[j + 1:], j + 1):
                    # Check for t-square pattern
                    squares = 0
                    oppositions = 0
                    
                    for aspect_list in [aspects[planet1], aspects[planet2], aspects[planet3]]:
                        for aspect in aspect_list:
                            if (aspect["planet1"] in [planet1, planet2, planet3] and
                                aspect["planet2"] in [planet1, planet2, planet3]):
                                if aspect["type"] == "Square":
                                    squares += 1
                                elif aspect["type"] == "Opposition":
                                    oppositions += 1
                    
                    if squares >= 2 and oppositions >= 1:
                        t_squares.append({
                            "type": "T-Square",
                            "planets": [planet1, planet2, planet3],
                            "description": f"T-square involving {planet1}, {planet2}, and {planet3}"
                        })
        
        return t_squares
    
    def _find_stelliums(self, aspects: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Find stellium patterns (3+ planets in same sign)

        Args:
            aspects: Dictionary of aspects by planet

        Returns:
            List of stellium patterns
        """
        stelliums = []
        sign_counts = {}
        
        # Count planets in each sign
        for planet, position in aspects.items():
            sign = position.get("sign", "")
            if sign:
                sign_counts[sign] = sign_counts.get(sign, []) + [planet]
        
        # Find signs with 3+ planets
        for sign, planets in sign_counts.items():
            if len(planets) >= 3:
                stelliums.append({
                    "type": "Stellium",
                    "sign": sign,
                    "planets": planets,
                    "description": f"Stellium in {sign}: {', '.join(planets)}"
                })
        
        return stelliums
    
    def get_aspect_summary(self, aspects: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Generate a summary of all aspects

        Args:
            aspects: Dictionary of aspects by planet

        Returns:
            Summary string
        """
        aspect_counts = {}
        total_aspects = 0
        
        for planet_aspects in aspects.values():
            for aspect in planet_aspects:
                aspect_type = aspect["type"]
                aspect_counts[aspect_type] = aspect_counts.get(aspect_type, 0) + 1
                total_aspects += 1
        
        if not aspect_counts:
            return "No major aspects found"
        
        summary_parts = []
        for aspect_type, count in aspect_counts.items():
            summary_parts.append(f"{count} {aspect_type}")
        
        return f"Total aspects: {total_aspects}. " + ", ".join(summary_parts) 