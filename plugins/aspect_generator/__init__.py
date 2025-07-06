"""
Aspect Generator Plugin for Outer Skies

This plugin generates AI-powered interpretations for astrological aspects
within a specified orb range.
"""

from .plugin import AspectGeneratorPlugin

# Plugin class that will be discovered by the plugin manager
Plugin = AspectGeneratorPlugin

__version__ = "1.0.0"
__author__ = "Outer Skies Team"

default_app_config = 'plugins.aspect_generator.apps.AspectGeneratorConfig'

def get_plugin():
    return AspectGeneratorPlugin() 