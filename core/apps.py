"""
Django App Configuration for Core Module
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core System'
    
    def ready(self):
        """Initialize core system when Django starts."""
        # Import signals and other initialization code here
        pass 