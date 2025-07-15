"""
Dignity Calculator Service

This service handles all dignity calculations for planets in signs.
Focused responsibility: Calculate dignities only.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Define dignity rulerships
DIGNITY_RULERSHIPS = {
    "Sun": {"Ruler": "Leo", "Exaltation": "Aries", "Fall": "Libra", "Detriment": "Aquarius"},
    "Moon": {"Ruler": "Cancer", "Exaltation": "Taurus", "Fall": "Scorpio", "Detriment": "Capricorn"},
    "Mercury": {"Ruler": ["Gemini", "Virgo"], "Exaltation": "Virgo", "Fall": "Pisces", "Detriment": ["Sagittarius", "Pisces"]},
    "Venus": {"Ruler": ["Taurus", "Libra"], "Exaltation": "Pisces", "Fall": "Virgo", "Detriment": ["Aries", "Scorpio"]},
    "Mars": {"Ruler": ["Aries", "Scorpio"], "Exaltation": "Capricorn", "Fall": "Cancer", "Detriment": ["Taurus", "Libra"]},
    "Jupiter": {"Ruler": ["Sagittarius", "Pisces"], "Exaltation": "Cancer", "Fall": "Capricorn", "Detriment": ["Gemini", "Virgo"]},
    "Saturn": {"Ruler": ["Capricorn", "Aquarius"], "Exaltation": "Libra", "Fall": "Aries", "Detriment": ["Cancer", "Leo"]},
    "Uranus": {"Ruler": "Aquarius", "Exaltation": "Scorpio", "Fall": "Taurus", "Detriment": "Leo"},
    "Neptune": {"Ruler": "Pisces", "Exaltation": "Cancer", "Fall": "Capricorn", "Detriment": "Virgo"},
    "Pluto": {"Ruler": "Scorpio", "Exaltation": "Aries", "Fall": "Libra", "Detriment": "Taurus"}
}

# Dignity scores for calculations
DIGNITY_SCORES = {
    "Ruler": 5,
    "Exaltation": 4,
    "Triplicity": 3,
    "Term": 2,
    "Face": 1,
    "Neutral": 0,
    "Face": -1,
    "Term": -2,
    "Detriment": -3,
    "Fall": -4
}


class DignityCalculator:
    """
    Focused service for dignity calculations
    """
    
    def __init__(self):
        self.dignity_rulerships = DIGNITY_RULERSHIPS.copy()
        self.dignity_scores = DIGNITY_SCORES.copy()
    
    def calculate_essential_dignity(self, planet: str, sign: str) -> Dict[str, Any]:
        """
        Calculate essential dignity for a planet in a sign

        Args:
            planet: Planet name
            sign: Sign name

        Returns:
            Dictionary with dignity information
        """
        dignities = self.dignity_rulerships.get(planet, {})
        
        # Check rulership
        ruler_signs = dignities.get("Ruler", [])
        if isinstance(ruler_signs, str):
            ruler_signs = [ruler_signs]
        
        if sign in ruler_signs:
            return {
                "dignity": "Ruler",
                "score": self.dignity_scores["Ruler"],
                "description": f"{planet} rules {sign}",
                "strength": "strong"
            }
        
        # Check exaltation
        exaltation_sign = dignities.get("Exaltation")
        if sign == exaltation_sign:
            return {
                "dignity": "Exaltation",
                "score": self.dignity_scores["Exaltation"],
                "description": f"{planet} is exalted in {sign}",
                "strength": "strong"
            }
        
        # Check detriment
        detriment_signs = dignities.get("Detriment", [])
        if isinstance(detriment_signs, str):
            detriment_signs = [detriment_signs]
        
        if sign in detriment_signs:
            return {
                "dignity": "Detriment",
                "score": self.dignity_scores["Detriment"],
                "description": f"{planet} is in detriment in {sign}",
                "strength": "weak"
            }
        
        # Check fall
        fall_sign = dignities.get("Fall")
        if sign == fall_sign:
            return {
                "dignity": "Fall",
                "score": self.dignity_scores["Fall"],
                "description": f"{planet} is in fall in {sign}",
                "strength": "weak"
            }
        
        # Neutral dignity
        return {
            "dignity": "Neutral",
            "score": self.dignity_scores["Neutral"],
            "description": f"{planet} is neutral in {sign}",
            "strength": "neutral"
        }
    
    def calculate_accidental_dignity(self, planet: str, position: Dict[str, Any], 
                                   house_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calculate accidental dignity based on house position and other factors

        Args:
            planet: Planet name
            position: Planet position data
            house_data: House data (optional)

        Returns:
            Dictionary with accidental dignity information
        """
        accidental_factors = []
        total_score = 0
        
        # House position dignity
        if house_data:
            house_number = position.get("house", 1)
            house_dignity = self._calculate_house_dignity(house_number)
            if house_dignity:
                accidental_factors.append(house_dignity)
                total_score += house_dignity.get("score", 0)
        
        # Angular house dignity (houses 1, 4, 7, 10 are angular)
        angular_houses = [1, 4, 7, 10]
        house_number = position.get("house", 1)
        if house_number in angular_houses:
            angular_dignity = {
                "factor": "Angular House",
                "score": 3,
                "description": f"{planet} in angular house {house_number}"
            }
            accidental_factors.append(angular_dignity)
            total_score += 3
        
        # Succedent house dignity (houses 2, 5, 8, 11 are succedent)
        succedent_houses = [2, 5, 8, 11]
        if house_number in succedent_houses:
            succedent_dignity = {
                "factor": "Succedent House",
                "score": 2,
                "description": f"{planet} in succedent house {house_number}"
            }
            accidental_factors.append(succedent_dignity)
            total_score += 2
        
        # Cadent house dignity (houses 3, 6, 9, 12 are cadent)
        cadent_houses = [3, 6, 9, 12]
        if house_number in cadent_houses:
            cadent_dignity = {
                "factor": "Cadent House",
                "score": 1,
                "description": f"{planet} in cadent house {house_number}"
            }
            accidental_factors.append(cadent_dignity)
            total_score += 1
        
        return {
            "factors": accidental_factors,
            "total_score": total_score,
            "strength": self._get_dignity_strength(total_score)
        }
    
    def _calculate_house_dignity(self, house_number: int) -> Optional[Dict[str, Any]]:
        """
        Calculate dignity based on house number

        Args:
            house_number: House number (1-12)

        Returns:
            House dignity information or None
        """
        house_dignities = {
            1: {"score": 5, "description": "First House - Strong dignity"},
            4: {"score": 4, "description": "Fourth House - Good dignity"},
            7: {"score": 4, "description": "Seventh House - Good dignity"},
            10: {"score": 5, "description": "Tenth House - Strong dignity"},
            2: {"score": 2, "description": "Second House - Moderate dignity"},
            5: {"score": 3, "description": "Fifth House - Good dignity"},
            8: {"score": 1, "description": "Eighth House - Weak dignity"},
            11: {"score": 2, "description": "Eleventh House - Moderate dignity"},
            3: {"score": 1, "description": "Third House - Weak dignity"},
            6: {"score": 0, "description": "Sixth House - Neutral dignity"},
            9: {"score": 2, "description": "Ninth House - Moderate dignity"},
            12: {"score": 0, "description": "Twelfth House - Neutral dignity"}
        }
        
        return house_dignities.get(house_number)
    
    def _get_dignity_strength(self, score: int) -> str:
        """
        Get dignity strength based on score

        Args:
            score: Dignity score

        Returns:
            Strength description
        """
        if score >= 5:
            return "very_strong"
        elif score >= 3:
            return "strong"
        elif score >= 1:
            return "moderate"
        elif score >= 0:
            return "neutral"
        elif score >= -2:
            return "weak"
        else:
            return "very_weak"
    
    def calculate_combined_dignity(self, planet: str, sign: str, 
                                 position: Dict[str, Any], 
                                 house_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calculate combined essential and accidental dignity

        Args:
            planet: Planet name
            sign: Sign name
            position: Planet position data
            house_data: House data (optional)

        Returns:
            Dictionary with combined dignity information
        """
        essential = self.calculate_essential_dignity(planet, sign)
        accidental = self.calculate_accidental_dignity(planet, position, house_data)
        
        total_score = essential["score"] + accidental["total_score"]
        
        return {
            "planet": planet,
            "sign": sign,
            "essential_dignity": essential,
            "accidental_dignity": accidental,
            "total_score": total_score,
            "overall_strength": self._get_dignity_strength(total_score),
            "summary": f"{planet} in {sign}: {essential['dignity']} (essential) + {accidental['total_score']} (accidental) = {total_score} total"
        }
    
    def calculate_all_dignities(self, positions: Dict[str, Dict[str, Any]], 
                              house_data: Dict[str, Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        Calculate dignities for all planets

        Args:
            positions: Dictionary of planet positions
            house_data: House data (optional)

        Returns:
            Dictionary mapping planets to their dignity information
        """
        dignities = {}
        
        for planet, position in positions.items():
            sign = position.get("sign", "")
            if sign:
                dignities[planet] = self.calculate_combined_dignity(
                    planet, sign, position, house_data
                )
        
        return dignities
    
    def get_dignity_summary(self, dignities: Dict[str, Dict[str, Any]]) -> str:
        """
        Generate a summary of all dignities

        Args:
            dignities: Dictionary of dignities by planet

        Returns:
            Summary string
        """
        if not dignities:
            return "No dignity information available"
        
        summary_parts = []
        for planet, dignity_info in dignities.items():
            essential = dignity_info["essential_dignity"]["dignity"]
            accidental_score = dignity_info["accidental_dignity"]["total_score"]
            total_score = dignity_info["total_score"]
            
            summary_parts.append(
                f"{planet}: {essential} (essential) + {accidental_score} (accidental) = {total_score}"
            )
        
        return "; ".join(summary_parts)
    
    def get_strongest_planets(self, dignities: Dict[str, Dict[str, Any]], 
                            limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get planets with strongest dignities

        Args:
            dignities: Dictionary of dignities by planet
            limit: Maximum number of planets to return

        Returns:
            List of planets sorted by dignity strength
        """
        sorted_planets = sorted(
            dignities.items(),
            key=lambda x: x[1]["total_score"],
            reverse=True
        )
        
        return [
            {
                "planet": planet,
                "dignity_info": dignity_info
            }
            for planet, dignity_info in sorted_planets[:limit]
        ]
    
    def get_weakest_planets(self, dignities: Dict[str, Dict[str, Any]], 
                          limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get planets with weakest dignities

        Args:
            dignities: Dictionary of dignities by planet
            limit: Maximum number of planets to return

        Returns:
            List of planets sorted by dignity weakness
        """
        sorted_planets = sorted(
            dignities.items(),
            key=lambda x: x[1]["total_score"]
        )
        
        return [
            {
                "planet": planet,
                "dignity_info": dignity_info
            }
            for planet, dignity_info in sorted_planets[:limit]
        ] 