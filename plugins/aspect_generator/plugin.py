"""
Aspect Generator Plugin

This plugin generates AI-powered interpretations for astrological aspects
within a specified orb range. It integrates with the chart generation system
to provide detailed aspect interpretations.
"""

import logging
from typing import Dict, Any, List, Optional
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import path
from plugins.base import BasePlugin
from ai_integration.openrouter_api import generate_interpretation

logger = logging.getLogger(__name__)


class AspectGeneratorPlugin(BasePlugin):
    """
    Aspect Generator Plugin for Outer Skies
    
    Generates AI-powered interpretations for astrological aspects within
    a specified orb range. Integrates with the chart generation system.
    """
    
    # Plugin metadata
    name = "Aspect Generator"
    version = "1.0.0"
    description = "Generates AI-powered interpretations for astrological aspects"
    author = "Outer Skies Team"
    website = "https://outer-skies.com"
    
    # Plugin configuration
    requires_auth = False
    admin_enabled = False
    api_enabled = True
    
    def __init__(self):
        super().__init__()
        self.default_orb = 8.0  # Default orb in degrees
        self.aspects_enabled = True
        
    def install(self):
        """Install the plugin"""
        logger.info("Installing Aspect Generator Plugin")
        # No database migrations needed for this plugin
        return True
        
    def uninstall(self):
        """Uninstall the plugin"""
        logger.info("Uninstalling Aspect Generator Plugin")
        return True
        
    def get_urls(self):
        """Return URL patterns for the plugin"""
        return [
            path('aspects/generate/', self.generate_aspects_view, name='generate_aspects'),
            path('aspects/settings/', self.aspect_settings_view, name='aspect_settings'),
        ]
        
    def get_api_urls(self):
        """Return API URL patterns for the plugin"""
        return [
            path('api/aspects/generate/', self.generate_aspects_api, name='api_generate_aspects'),
            path('api/aspects/settings/', self.aspect_settings_api, name='api_aspect_settings'),
        ]
        
    def get_context(self, request):
        """Return additional context data for templates"""
        return {
            'aspect_generator_enabled': self.aspects_enabled,
            'default_orb': self.default_orb,
        }
        
    def get_navigation_items(self, request):
        """Return navigation items for the main menu"""
        return [
            {
                'name': 'Aspect Generator',
                'url': '/aspects/settings/',
                'icon': 'aspects',
                'permission': None,
            }
        ]
        
    def get_dashboard_widgets(self, request):
        """Return dashboard widgets"""
        return [
            {
                'name': 'Aspect Generator',
                'template': 'aspect_generator/widget.html',
                'context': self.get_context(request),
            }
        ]
        
    def get_settings_form(self):
        """Return a form class for plugin settings"""
        from .forms import AspectGeneratorSettingsForm
        return AspectGeneratorSettingsForm
        
    def get_requirements(self):
        """Return plugin requirements"""
        return [
            'django>=4.2.0',
            'ai_integration',  # Requires the AI integration module
        ]
        
    def get_dependencies(self):
        """Return plugin dependencies"""
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
        """Return plugin information"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'website': self.website,
            'requires_auth': self.requires_auth,
            'admin_enabled': self.admin_enabled,
            'api_enabled': self.api_enabled,
        }
        
    # Plugin-specific methods
    
    def calculate_aspects(self, chart_data: Dict[str, Any], orb: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Calculate aspects between planets within the specified orb
        
        Args:
            chart_data: Chart data containing planet positions
            orb: Orb in degrees (defaults to plugin default)
            
        Returns:
            List of aspect dictionaries
        """
        if orb is None:
            orb = self.default_orb
        else:
            orb = float(orb)  # Ensure orb is always a float
            
        aspects = []
        positions = chart_data.get('planetary_positions', {})
        
        # Define major aspects and their angles
        major_aspects = {
            'conjunction': 0,
            'opposition': 180,
            'trine': 120,
            'square': 90,
            'sextile': 60,
        }
        
        # Get planet names (excluding asteroids for now)
        planets = [p for p in positions.keys() if p in [
            'Sun', 'Moon', 'Mercury', 'Venus', 'Mars', 
            'Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto'
        ]]
        
        # Calculate aspects between all planet pairs
        for i, planet1 in enumerate(planets):
            for planet2 in planets[i+1:]:
                pos1 = positions[planet1]['absolute_degree']
                pos2 = positions[planet2]['absolute_degree']
                
                # Calculate angular distance
                distance = abs(pos1 - pos2)
                if distance > 180:
                    distance = 360 - distance
                    
                # Check for aspects within orb
                for aspect_name, aspect_angle in major_aspects.items():
                    if abs(distance - aspect_angle) <= orb:
                        aspects.append({
                            'planet1': planet1,
                            'planet2': planet2,
                            'aspect': aspect_name,
                            'angle': aspect_angle,
                            'actual_distance': distance,
                            'orb': abs(distance - aspect_angle),
                            'planet1_pos': pos1,
                            'planet2_pos': pos2,
                        })
                        
        return aspects
        
    def generate_aspect_interpretation(self, aspect: Dict[str, Any], chart_data: Dict[str, Any], 
                                     model_name: Optional[str] = None, temperature: Optional[float] = None, 
                                     max_tokens: Optional[int] = None) -> str:
        """
        Generate AI interpretation for a specific aspect
        
        Args:
            aspect: Aspect dictionary
            chart_data: Full chart data
            model_name: AI model to use (should match main chart generation)
            temperature: Temperature setting (should match main chart generation)
            max_tokens: Max tokens setting (should match main chart generation)
            
        Returns:
            AI-generated interpretation string
        """
        # Get planet positions and house information
        positions = chart_data.get('planetary_positions', {})
        houses = chart_data.get('house_cusps', {})
        
        planet1 = aspect['planet1']
        planet2 = aspect['planet2']
        
        # Get planet details
        p1_data = positions.get(planet1, {})
        p2_data = positions.get(planet2, {})
        
        # Get house information
        p1_house = self._get_house_for_planet(p1_data.get('absolute_degree', 0), houses)
        p2_house = self._get_house_for_planet(p2_data.get('absolute_degree', 0), houses)
        
        # Determine aspect strength based on orb
        orb = aspect['orb']
        if orb <= 1.0:
            strength = "exact"
        elif orb <= 3.0:
            strength = "strong"
        elif orb <= 5.0:
            strength = "moderate"
        else:
            strength = "wide"
        
        # Create refined prompt for AI interpretation
        prompt = f"""
=== OUTER SKIES ASPECT INTERPRETATION ===

You are an expert astrologer providing a focused interpretation of a specific astrological aspect. Write in the Outer Skies style: clear, insightful, and accessible while maintaining astrological accuracy.

ASPECT DATA:
{planet1} in {p1_data.get('sign', 'Unknown Sign')} in the {p1_house} house
{aspect['aspect'].upper()} (exact angle: {aspect['angle']}°)
{planet2} in {p2_data.get('sign', 'Unknown Sign')} in the {p2_house} house
Orb: {orb:.1f}° ({strength} aspect)

INTERPRETATION GUIDELINES:
- First paragraph: Explain the core nature of this {aspect['aspect']} aspect and how these two planetary energies interact, considering their signs and houses
- Second paragraph: Describe the psychological and behavioral implications, including how this aspect manifests in daily life and personal development

WRITING STYLE:
- Use clear, accessible language with astrological accuracy
- Include practical examples of how this energy manifests
- Maintain a supportive, empowering tone
- Keep each paragraph focused and flowing
- Consider the aspect strength (orb) in your interpretation

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
                timeout=10  # Shorter timeout for aspect interpretations
            )
            return interpretation
        except Exception as e:
            logger.error(f"Failed to generate aspect interpretation: {e}")
            # Return a basic fallback interpretation
            return f"The {aspect['aspect']} between {planet1} and {planet2} creates a dynamic interaction between these planetary energies. This aspect influences how these forces work together in your chart."
            
    def _get_house_for_planet(self, longitude: float, houses: Dict[str, Any]) -> str:
        """Get house number for a given longitude"""
        try:
            # Debug logging
            logger.debug(f"Calculating house for longitude {longitude}, houses data: {houses}")
            
            # Handle different house data formats
            house_cusps = None
            if isinstance(houses, dict):
                if 'cusps' in houses:
                    house_cusps = houses['cusps']
                elif 'house_cusps' in houses:
                    house_cusps = houses['house_cusps']
            elif isinstance(houses, (list, tuple)):
                # Direct list/tuple of house cusps (as returned by get_ascendant_and_houses)
                house_cusps = houses
            
            logger.debug(f"Extracted house cusps: {house_cusps}")
            
            if house_cusps and len(house_cusps) >= 12:
                # Normalize longitude to 0-360 range
                normalized_long = longitude % 360
                
                # Find which house the planet is in
                for i in range(12):
                    current_cusp = house_cusps[i]
                    next_cusp = house_cusps[(i + 1) % 12]
                    
                    # Handle cusp crossing 0°
                    if current_cusp > next_cusp:
                        if normalized_long >= current_cusp or normalized_long < next_cusp:
                            house_num = i + 1
                            logger.debug(f"Planet at {normalized_long}° found in house {house_num} (cusp {current_cusp}° to {next_cusp}°)")
                            break
                    else:
                        if current_cusp <= normalized_long < next_cusp:
                            house_num = i + 1
                            logger.debug(f"Planet at {normalized_long}° found in house {house_num} (cusp {current_cusp}° to {next_cusp}°)")
                            break
                else:
                    # If we didn't find a house in the loop, find the nearest cusp
                    min_distance = float('inf')
                    house_num = 1
                    for i in range(12):
                        cusp = house_cusps[i]
                        distance = min(abs(normalized_long - cusp), abs(normalized_long - cusp + 360))
                        if distance < min_distance:
                            min_distance = distance
                            house_num = i + 1
                    logger.debug(f"Planet at {normalized_long}° assigned to nearest house {house_num} (distance {min_distance:.1f}°)")
                
                # Return ordinal house number
                if house_num == 1:
                    return "1st"
                elif house_num == 2:
                    return "2nd"
                elif house_num == 3:
                    return "3rd"
                else:
                    return f"{house_num}th"
            
            # If no house data available, try to get from chart data
            logger.warning(f"No house cusps found for longitude {longitude}")
            return "1st"  # Default fallback
        except Exception as e:
            logger.error(f"Error calculating house for longitude {longitude}: {e}")
            return "1st"
            
    # View methods
    
    def generate_aspects_view(self, request):
        """View for generating aspects"""
        if request.method == 'POST':
            return self.generate_aspects_api(request)
        
        # Render template and return HttpResponse
        html_content = self.render_template('aspect_generator/generate.html', {
            'orb': self.default_orb,
            'enabled': self.aspects_enabled,
        })
        return HttpResponse(html_content)
        
    def aspect_settings_view(self, request):
        """View for aspect settings"""
        if request.method == 'POST':
            return self.aspect_settings_api(request)
        
        # Render template and return HttpResponse
        html_content = self.render_template('aspect_generator/settings.html', {
            'orb': self.default_orb,
            'enabled': self.aspects_enabled,
        })
        return HttpResponse(html_content)
        
    def generate_aspects_api(self, request):
        """API endpoint for generating aspects"""
        try:
            # Get chart data from request
            chart_data = request.POST.get('chart_data')
            if not chart_data:
                return self.json_response({'error': 'No chart data provided'}, 400)
                
            # Parse chart data
            import json
            chart_data = json.loads(chart_data)
            
            # Get orb from request or use default
            orb = float(request.POST.get('orb', self.default_orb))
            
            # Calculate aspects
            aspects = self.calculate_aspects(chart_data, orb)
            
            # Generate interpretations if enabled
            if self.aspects_enabled:
                for aspect in aspects:
                    aspect['interpretation'] = self.generate_aspect_interpretation(aspect, chart_data)
                    
            return self.json_response({
                'aspects': aspects,
                'orb_used': orb,
                'total_aspects': len(aspects),
            })
            
        except Exception as e:
            logger.error(f"Error generating aspects: {e}")
            return self.json_response({'error': str(e)}, 500)
            
    def aspect_settings_api(self, request):
        """API endpoint for aspect settings"""
        try:
            if request.method == 'POST':
                # Update settings
                self.default_orb = float(request.POST.get('orb', self.default_orb))
                self.aspects_enabled = request.POST.get('enabled', 'false').lower() == 'true'
                
                return self.json_response({
                    'success': True,
                    'orb': self.default_orb,
                    'enabled': self.aspects_enabled,
                })
            else:
                # Get current settings
                return self.json_response({
                    'orb': self.default_orb,
                    'enabled': self.aspects_enabled,
                })
                
        except Exception as e:
            logger.error(f"Error updating aspect settings: {e}")
            return self.json_response({'error': str(e)}, 500) 