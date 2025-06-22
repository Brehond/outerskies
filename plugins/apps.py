"""
Django app configuration for the plugin system
"""

from django.apps import AppConfig
from django.conf import settings

class PluginsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plugins'
    verbose_name = 'Plugin System'

    def ready(self):
        """
        Initialize the plugin system when Django starts
        """
        # Import here to avoid circular imports
        from . import get_plugin_manager
        
        # Get the plugin manager
        plugin_manager = get_plugin_manager()
        
        # Auto-discover plugins if enabled
        if getattr(settings, 'PLUGIN_SETTINGS', {}).get('auto_discover', True):
            plugin_manager.discover_plugins()
            
            # Auto-install plugins if enabled
            if getattr(settings, 'PLUGIN_SETTINGS', {}).get('auto_install', False):
                for plugin_name in plugin_manager.plugins:
                    try:
                        plugin = plugin_manager.get_plugin(plugin_name)
                        if plugin:
                            plugin.install()
                    except Exception as e:
                        print(f"Failed to auto-install plugin {plugin_name}: {e}") 