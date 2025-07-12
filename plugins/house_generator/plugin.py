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

    def generate_house_interpretation(self, house_info: Dict[str, Any],
                                    chart_data: Dict[str, Any],
                                    model_name: Optional[str] = None,
                                    temperature: Optional[float] = None,
                                    max_t