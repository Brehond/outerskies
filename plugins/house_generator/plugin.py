"""
House Generator Plugin

This plugin generates AI-powered interpretations for each of the 12 astrological houses,
including house cusp signs and any planets present in each house.
"""

import logging
from typing import Dict, Any, List, Optional
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import path
from plugins.base import BasePlugin
from ai_integration.openrouter_api import generate_interpretation

logger = logging.getLogger(__name__)


class HouseGeneratorPlugin(BasePlugin):
    """
    House Generator Plugin for Outer Skies
    
    Generates AI-powered interpretations for each of the 12 astrological houses,
    including house cusp signs and any planets present in each house.
    """
    
    # Plugin metadata
    name = "House Generator"
    version = "1.0.0"
    description = "Generates AI-powered interpretations for each of the 12 astrological houses"
    author = "Outer Skies Team"
    website = "https://outer-skies.com"
    
    # Plugin configuration
    requires_auth = False
    admin_enabled = False
    api_enabled = True
    
    def __init__(self):
        super().__init__()
        self.houses_enabled = True
        self.include_planets = True
        
    def install(self):
        """Install the plugin"""
        logger.info("Installing House Generator Plugin")
        # No database migrations needed for this plugin
        return True
        
    def uninstall(self):
        """Uninstall the plugin"""
        logger.info("Uninstalling House Generator Plugin")
        return True
        
    def get_urls(self):
        """Return URL patterns for the plugin"""
        return [
            path('houses/generate/', self.generate_houses_view, name='generate_houses'),
            path('houses/settings/', self.house_settings_view, name='house_settings'),
        ]
        
    def get_api_urls(self):
        """Return API URL patterns for the plugin"""
        return [
            path('api/houses/generate/', self.generate_houses_api, name='api_generate_houses'),
            path('api/houses/settings/', self.house_settings_api, name='api_house_settings'),
        ]
        
    def get_context(self, request):
        """Get context data for the plugin"""
        return {
            'house_generator_enabled': self.houses_enabled,
            'include_planets': self.include_planets,
        }
        
    def get_navigation_items(self, request):
        """Get navigation items for the plugin"""
        return [
            {
                'name': 'House Generator',
                'url': '/houses/generate/',
                'icon': 'home',
                'description': 'Generate house interpretations'
            }
        ]
        
    def get_dashboard_widgets(self, request):
        """Get dashboard widgets for the plugin"""
        return [
            {
                'name': 'house_generator_widget',
                'template': 'house_generator/widget.html',
                'context': self.get_context(request)
            }
        ]
        
    def get_settings_form(self):
        """Get settings form for the plugin"""
        from .forms import HouseGeneratorSettingsForm
        return HouseGeneratorSettingsForm
        
    def get_requirements(self):
        """Get plugin requirements"""
        return [
            'django>=4.2.0',
            'ai_integration',  # Requires the AI integration module
        ]
        
    def get_dependencies(self):
        """Get plugin dependencies"""
        return [
            'chart',  # Depends on the chart app
            'ai_integration',  # Depends on AI integration
        ]
        
    def validate_installation(self):
        """Validate plugin installation"""
        try:
            # Check if required modules are available
            import ai_integration.openrouter_api
            return True, "Plugin installed successfully"
        except ImportError as e:
            return False, f"Missing dependency: {str(e)}"
        
    def get_plugin_info(self):
        """Get plugin information"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'website': self.website,
            'status': 'active' if self.houses_enabled else 'disabled'
        }
        
    # Plugin-specific methods
    
    def calculate_houses(self, chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Calculate house information and planets in each house
        
        Args:
            chart_data: Chart data containing house cusps and planet positions
            
        Returns:
            List of house dictionaries with planets
        """
        houses = []
        positions = chart_data.get('planetary_positions', {})
        house_cusps = self._get_house_cusps(chart_data)
        
        logger.debug(f"Chart data keys: {list(chart_data.keys())}")
        logger.debug(f"House cusps found: {len(house_cusps)}")
        logger.debug(f"Positions found: {list(positions.keys())}")
        
        if not house_cusps or len(house_cusps) < 12:
            logger.error("Invalid house cusps data")
            return houses
            
        # Process each house
        for house_num in range(1, 13):
            house_info = {
                'house_number': house_num,
                'cusp_degree': house_cusps[house_num - 1],
                'cusp_sign': self._get_sign_for_degree(house_cusps[house_num - 1]),
                'planets': []
            }
            
            # Find planets in this house
            house_planets = self._get_planets_in_house(house_num, house_cusps, positions)
            house_info['planets'] = house_planets
            
            houses.append(house_info)
            
        logger.debug(f"Calculated {len(houses)} houses")
        return houses
        
    def generate_house_interpretation(self, house_info: Dict[str, Any], chart_data: Dict[str, Any],
                                    model_name: Optional[str] = None, temperature: Optional[float] = None,
                                    max_tokens: Optional[int] = None) -> str:
        """
        Generate AI interpretation for a specific house
        
        Args:
            house_info: House information dictionary
            chart_data: Full chart data
            model_name: AI model to use (should match main chart generation)
            temperature: Temperature setting (should match main chart generation)
            max_tokens: Max tokens setting (should match main chart generation)
            
        Returns:
            AI-generated interpretation string
        """
        house_num = house_info['house_number']
        cusp_sign = house_info['cusp_sign']
        planets = house_info['planets']
        
        # Create planet descriptions
        planet_descriptions = []
        for planet in planets:
            planet_name = planet['name']
            planet_sign = planet['sign']
            planet_house = f"{house_num}{'st' if house_num == 1 else 'nd' if house_num == 2 else 'rd' if house_num == 3 else 'th'}"
            planet_descriptions.append(f"{planet_name} in {planet_sign} in the {planet_house} house")
        
        # Create refined prompt for AI interpretation
        prompt = f"""
=== OUTER SKIES HOUSE INTERPRETATION ===

You are an expert astrologer providing a focused interpretation of a specific astrological house. Write in the Outer Skies style: clear, insightful, and accessible while maintaining astrological accuracy.

HOUSE DATA:
{house_num}{'st' if house_num == 1 else 'nd' if house_num == 2 else 'rd' if house_num == 3 else 'th'} House in {cusp_sign}
{f"Planets in this house: {', '.join(planet_descriptions)}" if planet_descriptions else "No planets in this house"}

INTERPRETATION GUIDELINES:
- First paragraph: Explain the core nature of the {house_num}{'st' if house_num == 1 else 'nd' if house_num == 2 else 'rd' if house_num == 3 else 'th'} house in {cusp_sign} and what this house represents in the natal chart
- Second paragraph: Describe how the energies of this house manifest in daily life, including the influence of any planets present and their integration with the house cusp sign

WRITING STYLE:
- Use clear, accessible language with astrological accuracy
- Include practical examples of how this house energy manifests
- Maintain a supportive, empowering tone
- Keep each paragraph focused and flowing
- Consider the house number, cusp sign, and any planets present

FORMAT: Two well-developed paragraphs that provide meaningful astrological insight.

=== END PROMPT ===
        """
        
        try:
            # Use the same AI settings as the main chart generation with shorter timeout
            interpretation = generate_interpretation(
                prompt=prompt,
                model_name=model_name or "gpt-4",  # Default to gpt-4 if not specified
                temperature=temperature or 0.7,
                max_tokens=max_tokens or 300,
                timeout=10  # Shorter timeout for house interpretations
            )
            return interpretation
        except Exception as e:
            logger.error(f"Failed to generate house interpretation: {e}")
            # Return a basic fallback interpretation
            planet_text = f" with {', '.join([p['name'] for p in planets])}" if planets else ""
            return f"The {house_num}{'st' if house_num == 1 else 'nd' if house_num == 2 else 'rd' if house_num == 3 else 'th'} house in {cusp_sign}{planet_text} represents important life areas. This house governs key aspects of personal development and life experience."
            
    def _get_house_cusps(self, chart_data: Dict[str, Any]) -> List[float]:
        """Get house cusps from chart data"""
        # The ephemeris service returns houses as a list of floats
        # Use the correct key from chart_data
        houses = chart_data.get('house_cusps', [])
        
        logger.debug(f"Chart data type: {type(chart_data)}")
        logger.debug(f"Houses data type: {type(houses)}")
        logger.debug(f"Houses data: {houses}")
        logger.debug(f"Chart data keys: {list(chart_data.keys())}")
        
        # Handle list of floats (as returned by ephemeris service)
        if isinstance(houses, (list, tuple)) and len(houses) >= 12:
            logger.debug(f"Found {len(houses)} house cusps: {houses[:12]}")
            return list(houses[:12])  # Convert to list and return first 12 house cusps
        
        # Fallback for different formats
        if isinstance(houses, dict):
            if 'cusps' in houses:
                logger.debug(f"Found cusps in dict: {houses['cusps']}")
                return houses['cusps']
            elif 'house_cusps' in houses:
                logger.debug(f"Found house_cusps in dict: {houses['house_cusps']}")
                return houses['house_cusps']
        
        # If no houses found, try to get from ascendant data
        ascendant = chart_data.get('ascendant', {})
        if ascendant and 'absolute_degree' in ascendant:
            logger.error(f"No house cusps found for longitude {ascendant['absolute_degree']}")
        else:
            logger.error("No house cusps found and no ascendant data available")
        
        return []
        
    def _get_sign_for_degree(self, degree: float) -> str:
        """Get zodiac sign for a given degree"""
        signs = [
            'Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo',
            'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces'
        ]
        sign_index = int(degree / 30)
        return signs[sign_index % 12]
        
    def _get_planets_in_house(self, house_num: int, house_cusps: List[float], positions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get planets that are in a specific house"""
        planets_in_house = []
        
        if house_num < 1 or house_num > 12:
            return planets_in_house
            
        # Get house boundaries
        current_cusp = house_cusps[house_num - 1]
        next_cusp = house_cusps[house_num % 12]
        
        # Check each planet
        for planet_name, planet_data in positions.items():
            if planet_name in ['Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']:
                planet_longitude = planet_data.get('absolute_degree', 0)
                normalized_long = planet_longitude % 360
                
                # Check if planet is in this house
                in_house = False
                if current_cusp > next_cusp:  # House crosses 0°
                    if normalized_long >= current_cusp or normalized_long < next_cusp:
                        in_house = True
                else:
                    if current_cusp <= normalized_long < next_cusp:
                        in_house = True
                        
                if in_house:
                    planets_in_house.append({
                        'name': planet_name,
                        'sign': planet_data.get('sign', 'Unknown'),
                        'longitude': planet_longitude
                    })
                    
        return planets_in_house
        
    def generate_house_interpretations(self, chart_data: Dict[str, Any], include_planets: bool = True,
                                     model_name: Optional[str] = None, temperature: Optional[float] = None,
                                     max_tokens: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Generate AI interpretations for all 12 houses
        
        Args:
            chart_data: Chart data containing house cusps and planet positions
            include_planets: Whether to include planet information in interpretations
            model_name: AI model to use (should match main chart generation)
            temperature: Temperature setting (should match main chart generation)
            max_tokens: Max tokens setting (should match main chart generation)
            
        Returns:
            List of house dictionaries with interpretations
        """
        try:
            # Calculate house information
            houses = self.calculate_houses(chart_data)
            
            if not houses:
                logger.error("Failed to calculate houses")
                return []
            
            # Generate interpretations for each house
            for house in houses:
                try:
                    # Prepare house info for interpretation
                    house_info = {
                        'house_number': house['house_number'],
                        'cusp_sign': house['cusp_sign'],
                        'cusp_degree': house['cusp_degree'],
                        'planets': house['planets'] if include_planets else []
                    }
                    
                    # Generate AI interpretation
                    interpretation = self.generate_house_interpretation(
                        house_info, 
                        chart_data,
                        model_name=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    
                    # Add interpretation to house data
                    house['interpretation'] = interpretation
                    house['sign'] = house['cusp_sign']  # For template compatibility
                    house['cusp'] = house['cusp_degree']  # For template compatibility
                    
                except Exception as e:
                    logger.error(f"Failed to generate interpretation for house {house['house_number']}: {e}")
                    house['interpretation'] = f"Unable to generate interpretation for the {house['house_number']}{'st' if house['house_number'] == 1 else 'nd' if house['house_number'] == 2 else 'rd' if house['house_number'] == 3 else 'th'} house due to an error."
                    house['sign'] = house['cusp_sign']
                    house['cusp'] = house['cusp_degree']
            
            logger.info(f"Generated interpretations for {len(houses)} houses")
            return houses
            
        except Exception as e:
            logger.error(f"Failed to generate house interpretations: {e}")
            return []
        
    # View methods
    
    def generate_houses_view(self, request):
        """View for generating house interpretations"""
        if request.method == 'POST':
            return self.generate_houses_api(request)
        
        # Render template and return HttpResponse
        html_content = self.render_template('house_generator/generate.html', {
            'enabled': self.houses_enabled,
            'include_planets': self.include_planets,
        })
        return HttpResponse(html_content)
        
    def house_settings_view(self, request):
        """View for house settings"""
        if request.method == 'POST':
            return self.house_settings_api(request)
        
        # Render template and return HttpResponse
        html_content = self.render_template('house_generator/settings.html', {
            'enabled': self.houses_enabled,
            'include_planets': self.include_planets,
        })
        return HttpResponse(html_content)
        
    def generate_houses_api(self, request):
        """API endpoint for generating house interpretations"""
        try:
            # Get chart data from request
            chart_data = request.POST.get('chart_data')
            if not chart_data:
                return self.json_response({'error': 'No chart data provided'}, 400)
                
            # Parse chart data
            import json
            chart_data = json.loads(chart_data)
            
            # Calculate houses
            houses = self.calculate_houses(chart_data)
            
            # Generate interpretations if enabled
            if self.houses_enabled:
                for house in houses:
                    house['interpretation'] = self.generate_house_interpretation(house, chart_data)
                    
            return self.json_response({
                'houses': houses,
                'total_houses': len(houses),
            })
            
        except Exception as e:
            logger.error(f"Error generating house interpretations: {e}")
            return self.json_response({'error': str(e)}, 500)
            
    def house_settings_api(self, request):
        """API endpoint for house settings"""
        try:
            if request.method == 'POST':
                # Update settings
                self.houses_enabled = request.POST.get('enabled', 'false').lower() == 'true'
                self.include_planets = request.POST.get('include_planets', 'false').lower() == 'true'
                
                return self.json_response({
                    'success': True,
                    'enabled': self.houses_enabled,
                    'include_planets': self.include_planets,
                })
            else:
                # Get current settings
                return self.json_response({
                    'enabled': self.houses_enabled,
                    'include_planets': self.include_planets,
                })
                
        except Exception as e:
            logger.error(f"Error updating house settings: {e}")
            return self.json_response({'error': str(e)}, 500) 