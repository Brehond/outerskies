"""
Outer Skies Plugin System

This module provides a comprehensive plugin architecture for the Outer Skies
astrology application, allowing team members to develop features independently
and integrate them seamlessly.

Plugin Structure:
- Each plugin is a Django app in the plugins/ directory
- Plugins can register themselves with the main application
- Plugins can extend models, views, URLs, and templates
- Plugins can provide their own static files and migrations
"""

import os
import importlib
from django.conf import settings
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

class PluginManager:
    """
    Manages the registration and lifecycle of plugins
    """
    
    def __init__(self):
        self.plugins = {}
        self.registered_plugins = []
        self.plugin_hooks = {}
    
    def discover_plugins(self):
        """
        Automatically discover plugins in the plugins/ directory
        """
        plugins_dir = os.path.join(settings.BASE_DIR, 'plugins')
        if not os.path.exists(plugins_dir):
            return
        
        for item in os.listdir(plugins_dir):
            plugin_path = os.path.join(plugins_dir, item)
            if os.path.isdir(plugin_path) and not item.startswith('_'):
                # Skip management directory
                if item == 'management':
                    continue
                    
                # Check if it's a valid Django app
                if os.path.exists(os.path.join(plugin_path, '__init__.py')):
                    self.register_plugin(item)
    
    def register_plugin(self, plugin_name):
        """
        Register a plugin with the system
        """
        try:
            plugin_module = importlib.import_module(f'plugins.{plugin_name}')
            if hasattr(plugin_module, 'Plugin'):
                plugin_class = plugin_module.Plugin
                plugin_instance = plugin_class()
                self.plugins[plugin_name] = plugin_instance
                self.registered_plugins.append(plugin_name)
                
                # Register plugin hooks
                if hasattr(plugin_instance, 'hooks'):
                    for hook_name, hook_func in plugin_instance.hooks.items():
                        if hook_name not in self.plugin_hooks:
                            self.plugin_hooks[hook_name] = []
                        self.plugin_hooks[hook_name].append(hook_func)
                
                print(f"✅ Plugin '{plugin_name}' registered successfully")
            else:
                print(f"⚠️  Plugin '{plugin_name}' missing Plugin class")
        except ImportError as e:
            print(f"❌ Failed to import plugin '{plugin_name}': {e}")
        except Exception as e:
            print(f"❌ Failed to register plugin '{plugin_name}': {e}")
    
    def get_plugin(self, plugin_name):
        """
        Get a specific plugin instance
        """
        return self.plugins.get(plugin_name)
    
    def get_all_plugins(self):
        """
        Get all registered plugins
        """
        return self.plugins
    
    def execute_hook(self, hook_name, *args, **kwargs):
        """
        Execute all registered hooks for a given hook name
        """
        results = []
        if hook_name in self.plugin_hooks:
            for hook_func in self.plugin_hooks[hook_name]:
                try:
                    result = hook_func(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    print(f"❌ Hook '{hook_name}' failed: {e}")
        return results
    
    def get_plugin_urls(self):
        """
        Collect URLs from all plugins
        """
        urls = []
        for plugin_name, plugin in self.plugins.items():
            if hasattr(plugin, 'get_urls'):
                plugin_urls = plugin.get_urls()
                if plugin_urls:
                    urls.extend(plugin_urls)
        return urls
    
    def get_plugin_context(self, request):
        """
        Collect context data from all plugins
        """
        context = {}
        for plugin_name, plugin in self.plugins.items():
            if hasattr(plugin, 'get_context'):
                try:
                    plugin_context = plugin.get_context(request)
                    if plugin_context:
                        context.update(plugin_context)
                except Exception as e:
                    print(f"❌ Failed to get context from plugin '{plugin_name}': {e}")
        return context

# Global plugin manager instance
plugin_manager = PluginManager()

def get_plugin_manager():
    """
    Get the global plugin manager instance
    """
    return plugin_manager

def register_plugin_hook(hook_name, func):
    """
    Register a hook function for a specific hook name
    """
    if hook_name not in plugin_manager.plugin_hooks:
        plugin_manager.plugin_hooks[hook_name] = []
    plugin_manager.plugin_hooks[hook_name].append(func)

def execute_plugin_hook(hook_name, *args, **kwargs):
    """
    Execute all registered hooks for a given hook name
    """
    return plugin_manager.execute_hook(hook_name, *args, **kwargs) 