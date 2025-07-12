"""
Django app configuration for the house generator plugin
"""

from django.apps import AppConfig


class HouseGeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.house_generator'
    verbose_name = 'House Generator'

    def ready(self):
        """
        Initialize the house generator plugin when Django starts
        """
        # Import here to avoid circular imports
        from . import plugin
        return True
