"""
Base Plugin Class

This module provides the base class that all plugins should inherit from.
It defines the interface and common functionality for plugins.
"""

from abc import ABC, abstractmethod
from django.urls import path, include
from django.conf import settings
from django.template.loader import render_to_string
from django.http import JsonResponse
import os


class BasePlugin(ABC):
    """
    Base class for all Outer Skies plugins

    Plugins should inherit from this class and implement the required methods.
    """

    # Plugin metadata
    name = "Base Plugin"
    version = "1.0.0"
    description = "Base plugin class"
    author = "Outer Skies Team"
    website = "https://outer-skies.com"

    # Plugin configuration
    requires_auth = False  # Whether the plugin requires authentication
    admin_enabled = False  # Whether the plugin has admin interface
    api_enabled = False    # Whether the plugin provides API endpoints

    def __init__(self):
        # Get the plugin directory more reliably
        try:
            # Try to get the module file path
            module = self.__class__.__module__
            if module.startswith('plugins.'):
                plugin_name = module.split('.')[1]
                self.plugin_dir = os.path.join(settings.BASE_DIR, 'plugins', plugin_name)
            else:
                # Fallback to current directory
                self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        except:
            # Fallback to current directory
            self.plugin_dir = os.path.dirname(os.path.abspath(__file__))

        self.template_dir = os.path.join(self.plugin_dir, 'templates')
        self.static_dir = os.path.join(self.plugin_dir, 'static')
        self.migrations_dir = os.path.join(self.plugin_dir, 'migrations')

        # Initialize hooks dictionary
        self.hooks = {}
        self._register_default_hooks()

    def _register_default_hooks(self):
        """
        Register default hooks that all plugins can use
        """
        self.hooks = {
            'on_user_login': [],
            'on_user_logout': [],
            'on_chart_generated': [],
            'on_profile_updated': [],
            'before_template_render': [],
            'after_template_render': [],
            'on_api_request': [],
            'on_api_response': [],
        }

    @abstractmethod
    def install(self):
        """
        Install the plugin - called when plugin is first activated
        Should handle database migrations, initial setup, etc.
        """
        pass

    @abstractmethod
    def uninstall(self):
        """
        Uninstall the plugin - called when plugin is deactivated
        Should clean up any plugin-specific data
        """
        pass

    def get_urls(self):
        """
        Return URL patterns for the plugin
        Override this method to provide custom URLs
        """
        return []

    def get_admin_urls(self):
        """
        Return admin URL patterns for the plugin
        Override this method to provide admin interface URLs
        """
        return []

    def get_api_urls(self):
        """
        Return API URL patterns for the plugin
        Override this method to provide API endpoints
        """
        return []

    def get_context(self, request):
        """
        Return additional context data for templates
        Override this method to provide custom context
        """
        return {}

    def get_navigation_items(self, request):
        """
        Return navigation items for the main menu
        Override this method to add menu items
        """
        return []

    def get_dashboard_widgets(self, request):
        """
        Return dashboard widgets
        Override this method to add dashboard widgets
        """
        return []

    def get_settings_form(self):
        """
        Return a form class for plugin settings
        Override this method to provide settings interface
        """
        return None

    def get_permissions(self):
        """
        Return custom permissions for the plugin
        Override this method to define custom permissions
        """
        return []

    def get_migrations(self):
        """
        Return custom migrations for the plugin
        Override this method to provide custom migrations
        """
        return []

    def get_static_files(self):
        """
        Return static files that should be collected
        Override this method to provide custom static files
        """
        return []

    def get_templates(self):
        """
        Return template directories that should be included
        Override this method to provide custom templates
        """
        return []

    def get_models(self):
        """
        Return model classes for the plugin
        Override this method to provide custom models
        """
        return []

    def get_forms(self):
        """
        Return form classes for the plugin
        Override this method to provide custom forms
        """
        return []

    def get_views(self):
        """
        Return view classes for the plugin
        Override this method to provide custom views
        """
        return []

    def get_middleware(self):
        """
        Return middleware classes for the plugin
        Override this method to provide custom middleware
        """
        return []

    def get_commands(self):
        """
        Return management command classes for the plugin
        Override this method to provide custom commands
        """
        return []

    def get_signals(self):
        """
        Return signal handlers for the plugin
        Override this method to provide custom signal handlers
        """
        return []

    def get_celery_tasks(self):
        """
        Return Celery task classes for the plugin
        Override this method to provide custom tasks
        """
        return []

    def get_health_checks(self):
        """
        Return health check functions for the plugin
        Override this method to provide custom health checks
        """
        return []

    def get_metrics(self):
        """
        Return metrics functions for the plugin
        Override this method to provide custom metrics
        """
        return []

    def get_webhooks(self):
        """
        Return webhook handlers for the plugin
        Override this method to provide custom webhooks
        """
        return []

    def get_scheduled_tasks(self):
        """
        Return scheduled task configurations for the plugin
        Override this method to provide custom scheduled tasks
        """
        return []

    def get_cache_keys(self):
        """
        Return cache key patterns for the plugin
        Override this method to provide custom cache keys
        """
        return []

    def get_settings(self):
        """
        Return settings dictionary for the plugin
        Override this method to provide custom settings
        """
        return {}

    def get_requirements(self):
        """
        Return requirements list for the plugin
        Override this method to provide custom requirements
        """
        return []

    def get_dependencies(self):
        """
        Return dependency list for the plugin
        Override this method to provide custom dependencies
        """
        return []

    def validate_installation(self):
        """
        Validate that the plugin is properly installed
        Override this method to provide custom validation
        """
        return True

    def get_plugin_info(self):
        """
        Return plugin information dictionary
        """
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

    def render_template(self, template_name, context=None):
        """
        Render a template with the given context
        """
        if context is None:
            context = {}

        # Add plugin context
        context.update(self.get_context(None))

        # Try plugin-specific template first
        plugin_template = f"{self.__class__.__module__.split('.')[1]}/{template_name}"
        try:
            return render_to_string(plugin_template, context)
        except:
            # Fall back to global template
            return render_to_string(template_name, context)

    def json_response(self, data, status=200):
        """
        Return a JSON response
        """
        return JsonResponse(data, status=status)

    def log(self, message, level='info'):
        """
        Log a message with the plugin name
        """
        import logging
        logger = logging.getLogger(f"plugin.{self.__class__.__name__}")
        getattr(logger, level)(f"[{self.name}] {message}")

    def get_setting(self, key, default=None):
        """
        Get a plugin setting
        """
        plugin_settings = getattr(settings, 'PLUGIN_SETTINGS', {})
        plugin_name = self.__class__.__name__.lower()
        return plugin_settings.get(plugin_name, {}).get(key, default)

    def set_setting(self, key, value):
        """
        Set a plugin setting
        """
        if not hasattr(settings, 'PLUGIN_SETTINGS'):
            settings.PLUGIN_SETTINGS = {}

        plugin_name = self.__class__.__name__.lower()
        if plugin_name not in settings.PLUGIN_SETTINGS:
            settings.PLUGIN_SETTINGS[plugin_name] = {}

        settings.PLUGIN_SETTINGS[plugin_name][key] = value
