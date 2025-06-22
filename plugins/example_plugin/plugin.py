"""
Example Plugin Implementation

This demonstrates how to create a plugin for Outer Skies.
"""

from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from plugins.base import BasePlugin


class ExamplePlugin(BasePlugin):
    """
    Example plugin that demonstrates plugin functionality
    """

    name = "Example Plugin"
    version = "1.0.0"
    description = "An example plugin demonstrating the plugin system"
    author = "Outer Skies Team"
    website = "https://outer-skies.com"

    requires_auth = True
    admin_enabled = True
    api_enabled = True

    def install(self):
        """
        Install the plugin
        """
        self.log("Installing Example Plugin")
        # Add any installation logic here
        # e.g., create default settings, database tables, etc.
        return True

    def uninstall(self):
        """
        Uninstall the plugin
        """
        self.log("Uninstalling Example Plugin")
        # Add any cleanup logic here
        # e.g., remove database tables, settings, etc.
        return True

    def get_urls(self):
        """
        Return URL patterns for the plugin
        """
        return [
            path('example/', self.example_view, name='example_plugin_view'),
            path('example/api/', self.example_api_view, name='example_plugin_api'),
        ]

    def get_navigation_items(self, request):
        """
        Add navigation items to the main menu
        """
        if request.user.is_authenticated:
            return [
                {
                    'name': 'Example Plugin',
                    'url': '/example/',
                    'icon': 'star',
                    'order': 100,
                }
            ]
        return []

    def get_dashboard_widgets(self, request):
        """
        Add widgets to the dashboard
        """
        if request.user.is_authenticated:
            return [
                {
                    'name': 'Example Widget',
                    'template': 'example_plugin/widget.html',
                    'context': {'message': 'Hello from Example Plugin!'},
                    'order': 1,
                }
            ]
        return []

    def get_context(self, request):
        """
        Add context data to templates
        """
        return {
            'example_plugin_enabled': True,
            'example_message': 'Hello from Example Plugin!',
        }

    def example_view(self, request):
        """
        Example view for the plugin
        """
        context = {
            'title': 'Example Plugin',
            'message': 'This is an example plugin view!',
        }
        return render(request, 'example_plugin/example.html', context)

    def example_api_view(self, request):
        """
        Example API endpoint for the plugin
        """
        return JsonResponse({
            'status': 'success',
            'message': 'Hello from Example Plugin API!',
            'plugin_info': self.get_plugin_info(),
        })

    def get_settings_form(self):
        """
        Return a form for plugin settings
        """
        from django import forms

        class ExamplePluginSettingsForm(forms.Form):
            example_setting = forms.CharField(
                max_length=100,
                required=False,
                help_text="An example setting for the plugin"
            )
            enable_feature = forms.BooleanField(
                required=False,
                help_text="Enable example feature"
            )

        return ExamplePluginSettingsForm

    def get_requirements(self):
        """
        Return additional requirements for this plugin
        """
        return [
            'requests>=2.25.0',
            'python-dateutil>=2.8.0',
        ]

    def get_dependencies(self):
        """
        Return other plugins this plugin depends on
        """
        return []  # No dependencies for this example

    def validate_installation(self):
        """
        Validate that the plugin is properly installed
        """
        # Add validation logic here
        return True, "Example Plugin is properly installed" 