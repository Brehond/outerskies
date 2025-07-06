from django.apps import AppConfig


class AspectGeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins.aspect_generator'
    verbose_name = 'Aspect Generator Plugin'
    
    def ready(self):
        """Initialize the plugin when Django is ready"""
        try:
            from .plugin import AspectGeneratorPlugin
            # Plugin will be automatically discovered by the plugin manager
        except ImportError:
            pass 

        # Import signals or perform any initialization
        pass 