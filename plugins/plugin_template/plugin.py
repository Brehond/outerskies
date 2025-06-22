"""
Plugin Template Implementation

This is a template that team members can copy and modify to create their own plugins.
Replace all instances of 'PluginTemplate' with your plugin name.
"""

from django.urls import path
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from plugins.base import BasePlugin

class PluginTemplate(BasePlugin):
    """
    Template plugin - replace with your actual plugin functionality
    """
    
    # TODO: Update these with your plugin information
    name = "Plugin Template"
    version = "1.0.0"
    description = "A template for creating new plugins"
    author = "Your Name"
    website = "https://your-website.com"
    
    # TODO: Configure these based on your plugin needs
    requires_auth = True  # Set to False if no authentication needed
    admin_enabled = False  # Set to True if you need admin interface
    api_enabled = False    # Set to True if you need API endpoints
    
    def install(self):
        """
        Install the plugin - called when plugin is first activated
        """
        self.log("Installing Plugin Template")
        
        # TODO: Add your installation logic here
        # Examples:
        # - Create database tables
        # - Set up default settings
        # - Create initial data
        # - Register signals
        
        return True
    
    def uninstall(self):
        """
        Uninstall the plugin - called when plugin is deactivated
        """
        self.log("Uninstalling Plugin Template")
        
        # TODO: Add your cleanup logic here
        # Examples:
        # - Remove database tables
        # - Clean up settings
        # - Remove files
        # - Unregister signals
        
        return True
    
    def get_urls(self):
        """
        Return URL patterns for the plugin
        """
        # TODO: Add your URL patterns here
        return [
            # path('your-endpoint/', self.your_view, name='your_view_name'),
        ]
    
    def get_navigation_items(self, request):
        """
        Add navigation items to the main menu
        """
        # TODO: Add navigation items if needed
        if request.user.is_authenticated and self.requires_auth:
            return [
                # {
                #     'name': 'Your Plugin',
                #     'url': '/your-plugin/',
                #     'icon': 'star',
                #     'order': 100,
                # }
            ]
        return []
    
    def get_dashboard_widgets(self, request):
        """
        Add widgets to the dashboard
        """
        # TODO: Add dashboard widgets if needed
        if request.user.is_authenticated and self.requires_auth:
            return [
                # {
                #     'name': 'Your Widget',
                #     'template': 'your_plugin/widget.html',
                #     'context': {'data': 'your data'},
                #     'order': 1,
                # }
            ]
        return []
    
    def get_context(self, request):
        """
        Add context data to templates
        """
        # TODO: Add context data if needed
        return {
            # 'your_plugin_enabled': True,
            # 'your_data': 'your value',
        }
    
    def get_settings_form(self):
        """
        Return a form for plugin settings
        """
        # TODO: Add settings form if needed
        # from django import forms
        # 
        # class YourPluginSettingsForm(forms.Form):
        #     setting_name = forms.CharField(
        #         max_length=100,
        #         required=False,
        #         help_text="Description of setting"
        #     )
        # 
        # return YourPluginSettingsForm
        
        return None
    
    def get_requirements(self):
        """
        Return additional requirements for this plugin
        """
        # TODO: Add any additional Python packages your plugin needs
        return [
            # 'requests>=2.25.0',
            # 'python-dateutil>=2.8.0',
        ]
    
    def get_dependencies(self):
        """
        Return other plugins this plugin depends on
        """
        # TODO: Add any other plugins this plugin depends on
        return []
    
    def validate_installation(self):
        """
        Validate that the plugin is properly installed
        """
        # TODO: Add validation logic
        return True, "Plugin Template is properly installed"
    
    # TODO: Add your custom methods below
    
    # def your_view(self, request):
    #     """
    #     Example view method
    #     """
    #     context = {
    #         'title': 'Your Plugin',
    #         'message': 'Hello from your plugin!',
    #     }
    #     return render(request, 'your_plugin/your_template.html', context)
    
    # def your_api_view(self, request):
    #     """
    #     Example API endpoint
    #     """
    #     return JsonResponse({
    #         'status': 'success',
    #         'message': 'Hello from your plugin API!',
    #     }) 