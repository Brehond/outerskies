from django.apps import AppConfig


class HouseGeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.house_generator'
    verbose_name = 'House Generator Plugin'
    
    def ready(self):
        """Initialize the plugin when Django is ready"""
        try:
            from .plugin import HouseGeneratorPlugin
            # Plugin will be automatically discovered by the plugin manager
        except ImportError:
            pass 