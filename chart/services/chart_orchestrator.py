"""
Chart Orchestrator Service

This service orchestrates all chart calculations by coordinating the focused services.
Main responsibility: Coordinate and orchestrate chart calculations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import swisseph as swe

from .planetary_calculator import PlanetaryCalculator
from .house_calculator import HouseCalculator
from .aspect_calculator import AspectCalculator
from .dignity_calculator import DignityCalculator
from .caching_service import ChartCachingService

logger = logging.getLogger(__name__)


class ChartOrchestrator:
    """
    Main orchestrator for chart calculations
    """
    
    def __init__(self, use_cache: bool = True, cache_timeout: int = 3600):
        # Initialize focused services
        self.planetary_calculator = PlanetaryCalculator()
        self.house_calculator = HouseCalculator()
        self.aspect_calculator = AspectCalculator()
        self.dignity_calculator = DignityCalculator()
        self.caching_service = ChartCachingService(cache_timeout) if use_cache else None
        
        # Set Swiss Ephemeris path
        self._init_swiss_ephemeris()
    
    def _init_swiss_ephemeris(self):
        """
        Initialize Swiss Ephemeris with proper path
        """
        try:
            # Set ephemeris path - adjust as needed for your setup
            swe.set_ephe_path('./ephemeris/ephe')
            logger.info("Swiss Ephemeris initialized successfully")
        except Exception as e:
            logger.warning(f"Could not set ephemeris path: {e}")
    
    def calculate_complete_chart(self, birth_date: datetime, latitude: float, longitude: float,
                               house_system: str = "Placidus", include_aspects: bool = True,
                               include_dignities: bool = True) -> Dict[str, Any]:
        """
        Calculate a complete natal chart

        Args:
            birth_date: Birth date and time
            latitude: Birth latitude
            longitude: Birth longitude
            house_system: House system to use
            include_aspects: Whether to calculate aspects
            include_dignities: Whether to calculate dignities

        Returns:
            Complete chart data
        """
        try:
            # Convert date to Julian Day
            jd = self._date_to_julian_day(birth_date)
            
            # Calculate planetary positions
            planetary_positions = self._calculate_planetary_positions(jd)
            
            # Calculate houses
            house_data = self._calculate_houses(jd, latitude, longitude, house_system)
            
            # Assign planets to houses
            planets_with_houses = self.house_calculator.assign_planets_to_houses(
                planetary_positions, house_data
            )
            
            # Initialize result
            chart_data = {
                "birth_data": {
                    "date": birth_date.isoformat(),
                    "latitude": latitude,
                    "longitude": longitude,
                    "julian_day": jd
                },
                "house_system": house_system,
                "planets": planets_with_houses,
                "houses": house_data,
                "calculated_at": datetime.now().isoformat()
            }
            
            # Calculate aspects if requested
            if include_aspects:
                aspects = self._calculate_aspects(planetary_positions)
                chart_data["aspects"] = aspects
                
                # Find aspect patterns
                patterns = self.aspect_calculator.find_aspect_patterns(aspects, planetary_positions)
                chart_data["aspect_patterns"] = patterns
            
            # Calculate dignities if requested
            if include_dignities:
                dignities = self._calculate_dignities(planets_with_houses, house_data)
                chart_data["dignities"] = dignities
            
            # Add summaries
            chart_data["summaries"] = self._generate_summaries(chart_data)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"Error calculating complete chart: {e}")
            raise
    
    def _date_to_julian_day(self, date: datetime) -> float:
        """
        Convert datetime to Julian Day

        Args:
            date: Datetime object

        Returns:
            Julian Day as float
        """
        return swe.julday(
            date.year, date.month, date.day,
            date.hour + date.minute / 60.0 + date.second / 3600.0
        )
    
    def _calculate_planetary_positions(self, jd: float) -> Dict[str, Any]:
        """
        Calculate planetary positions with caching

        Args:
            jd: Julian Day

        Returns:
            Planetary positions
        """
        # Try cache first
        if self.caching_service:
            cached_positions = self.caching_service.get_cached_planetary_positions(jd)
            if cached_positions:
                logger.debug("Using cached planetary positions")
                return cached_positions
        
        # Calculate fresh positions
        logger.debug("Calculating fresh planetary positions")
        positions = self.planetary_calculator.calculate_all_planetary_positions(jd)
        
        # Cache the result
        if self.caching_service:
            self.caching_service.cache_planetary_positions(jd, positions)
        
        return positions
    
    def _calculate_houses(self, jd: float, latitude: float, longitude: float, 
                         house_system: str) -> Dict[str, Any]:
        """
        Calculate house positions with caching

        Args:
            jd: Julian Day
            latitude: Latitude
            longitude: Longitude
            house_system: House system

        Returns:
            House data
        """
        # Try cache first
        if self.caching_service:
            cached_houses = self.caching_service.get_cached_house_positions(
                jd, latitude, longitude, house_system
            )
            if cached_houses:
                logger.debug("Using cached house positions")
                return cached_houses
        
        # Calculate fresh houses
        logger.debug("Calculating fresh house positions")
        house_data = self.house_calculator.calculate_houses(jd, latitude, longitude, house_system)
        
        # Cache the result
        if self.caching_service:
            self.caching_service.cache_house_positions(jd, latitude, longitude, house_system, house_data)
        
        return house_data
    
    def _calculate_aspects(self, planetary_positions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate aspects with caching

        Args:
            planetary_positions: Planetary positions

        Returns:
            Aspect data
        """
        # Try cache first
        if self.caching_service:
            cached_aspects = self.caching_service.get_cached_aspects(planetary_positions)
            if cached_aspects:
                logger.debug("Using cached aspects")
                return cached_aspects
        
        # Calculate fresh aspects
        logger.debug("Calculating fresh aspects")
        aspects = self.aspect_calculator.calculate_all_aspects(planetary_positions)
        
        # Cache the result
        if self.caching_service:
            self.caching_service.cache_aspects(planetary_positions, aspects)
        
        return aspects
    
    def _calculate_dignities(self, planetary_positions: Dict[str, Any], 
                           house_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate dignities with caching

        Args:
            planetary_positions: Planetary positions with houses
            house_data: House data

        Returns:
            Dignity data
        """
        # Try cache first
        if self.caching_service:
            cached_dignities = self.caching_service.get_cached_dignities(planetary_positions)
            if cached_dignities:
                logger.debug("Using cached dignities")
                return cached_dignities
        
        # Calculate fresh dignities
        logger.debug("Calculating fresh dignities")
        dignities = self.dignity_calculator.calculate_all_dignities(planetary_positions, house_data)
        
        # Cache the result
        if self.caching_service:
            self.caching_service.cache_dignities(planetary_positions, dignities)
        
        return dignities
    
    def _generate_summaries(self, chart_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate summary information for the chart

        Args:
            chart_data: Complete chart data

        Returns:
            Dictionary of summaries
        """
        summaries = {}
        
        # House summary
        if "houses" in chart_data:
            summaries["houses"] = self.house_calculator.get_house_summary(chart_data["houses"])
        
        # Aspect summary
        if "aspects" in chart_data:
            summaries["aspects"] = self.aspect_calculator.get_aspect_summary(chart_data["aspects"])
        
        # Dignity summary
        if "dignities" in chart_data:
            summaries["dignities"] = self.dignity_calculator.get_dignity_summary(chart_data["dignities"])
        
        # Planet summary
        planets = chart_data.get("planets", {})
        planet_summary = []
        for planet, data in planets.items():
            sign = data.get("sign", "Unknown")
            house = data.get("house", "Unknown")
            planet_summary.append(f"{planet}: {sign} (House {house})")
        summaries["planets"] = "; ".join(planet_summary)
        
        return summaries
    
    def calculate_specific_planet(self, birth_date: datetime, planet_name: str) -> Dict[str, Any]:
        """
        Calculate position for a specific planet

        Args:
            birth_date: Birth date and time
            planet_name: Name of the planet

        Returns:
            Planet position data
        """
        jd = self._date_to_julian_day(birth_date)
        
        if not self.planetary_calculator.validate_planet_name(planet_name):
            raise ValueError(f"Invalid planet name: {planet_name}")
        
        return self.planetary_calculator.calculate_planet_position(jd, planet_name)
    
    def calculate_aspects_between_planets(self, birth_date: datetime, planet1: str, planet2: str) -> List[Dict[str, Any]]:
        """
        Calculate aspects between two specific planets

        Args:
            birth_date: Birth date and time
            planet1: First planet name
            planet2: Second planet name

        Returns:
            List of aspects between the planets
        """
        jd = self._date_to_julian_day(birth_date)
        
        # Get positions for both planets
        pos1 = self.planetary_calculator.calculate_planet_position(jd, planet1)
        pos2 = self.planetary_calculator.calculate_planet_position(jd, planet2)
        
        return self.aspect_calculator.find_aspects_between_planets(
            pos1["absolute_degree"], pos2["absolute_degree"], planet1, planet2
        )
    
    def get_chart_statistics(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistics for a chart

        Args:
            chart_data: Complete chart data

        Returns:
            Chart statistics
        """
        stats = {
            "total_planets": len(chart_data.get("planets", {})),
            "house_system": chart_data.get("house_system", "Unknown"),
            "has_aspects": "aspects" in chart_data,
            "has_dignities": "dignities" in chart_data
        }
        
        # Count aspects
        if "aspects" in chart_data:
            total_aspects = 0
            for planet_aspects in chart_data["aspects"].values():
                total_aspects += len(planet_aspects)
            stats["total_aspects"] = total_aspects
        
        # Count aspect patterns
        if "aspect_patterns" in chart_data:
            stats["aspect_patterns"] = len(chart_data["aspect_patterns"])
        
        # Planet distribution by sign
        sign_distribution = {}
        for planet, data in chart_data.get("planets", {}).items():
            sign = data.get("sign", "Unknown")
            sign_distribution[sign] = sign_distribution.get(sign, 0) + 1
        stats["sign_distribution"] = sign_distribution
        
        # Planet distribution by house
        house_distribution = {}
        for planet, data in chart_data.get("planets", {}).items():
            house = data.get("house", "Unknown")
            house_distribution[house] = house_distribution.get(house, 0) + 1
        stats["house_distribution"] = house_distribution
        
        return stats
    
    def clear_cache(self) -> bool:
        """
        Clear all chart calculation cache

        Returns:
            True if successful
        """
        if self.caching_service:
            return self.caching_service.clear_all_chart_cache()
        return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Cache statistics
        """
        if self.caching_service:
            return self.caching_service.get_cache_stats()
        return {"caching_enabled": False}
    
    def validate_chart_data(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate chart data for completeness and correctness

        Args:
            chart_data: Chart data to validate

        Returns:
            Validation results
        """
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = ["birth_data", "planets", "houses"]
        for field in required_fields:
            if field not in chart_data:
                validation["is_valid"] = False
                validation["errors"].append(f"Missing required field: {field}")
        
        # Check planetary data
        if "planets" in chart_data:
            planets = chart_data["planets"]
            expected_planets = self.planetary_calculator.get_planet_list()
            
            for planet in expected_planets:
                if planet not in planets:
                    validation["warnings"].append(f"Missing planet: {planet}")
                else:
                    planet_data = planets[planet]
                    required_planet_fields = ["sign", "degree_in_sign", "absolute_degree"]
                    for field in required_planet_fields:
                        if field not in planet_data:
                            validation["errors"].append(f"Missing {field} for {planet}")
        
        # Check house data
        if "houses" in chart_data:
            houses = chart_data["houses"]
            if "cusps" not in houses:
                validation["errors"].append("Missing house cusps")
            elif len(houses["cusps"]) != 12:
                validation["warnings"].append("Expected 12 house cusps")
        
        return validation 