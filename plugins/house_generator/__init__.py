"""
House Generator Plugin for Outer Skies

This plugin generates AI-powered interpretations for each of the 12 astrological houses,
including house cusp signs and any planets present in each house.
"""

from .plugin import HouseGeneratorPlugin

# Plugin class that will be discovered by the plugin manager
Plugin = HouseGeneratorPlugin

__version__ = "1.0.0"
__author__ = "Outer Skies Team" 