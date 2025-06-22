# Outer Skies Plugin System Guide

## Overview

The Outer Skies plugin system allows team members to develop features independently and integrate them seamlessly into the main application. This modular architecture supports Docker deployment and enables easy collaboration.

## Architecture

### Plugin Structure
```
plugins/
├── __init__.py              # Plugin system initialization
├── base.py                  # Base plugin class
├── management/              # Management commands
│   └── commands/
│       └── manage_plugins.py
├── example_plugin/          # Example plugin
│   ├── __init__.py
│   ├── plugin.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   │   └── example_plugin/
│   └── static/
│       └── example_plugin/
└── your_plugin/             # Your custom plugin
    ├── __init__.py
    ├── plugin.py
    └── ...
```

## Creating a Plugin

### 1. Basic Plugin Structure

Create a new directory in `plugins/` with your plugin name:

```python
# plugins/your_plugin/__init__.py
from .plugin import YourPlugin

Plugin = YourPlugin
```

### 2. Plugin Class

```python
# plugins/your_plugin/plugin.py
from plugins.base import BasePlugin
from django.urls import path
from django.shortcuts import render

class YourPlugin(BasePlugin):
    name = "Your Plugin"
    version = "1.0.0"
    description = "Description of your plugin"
    author = "Your Name"
    website = "https://your-website.com"
    
    requires_auth = True  # Whether authentication is required
    admin_enabled = True  # Whether admin interface is provided
    api_enabled = True    # Whether API endpoints are provided
    
    def install(self):
        """Install the plugin"""
        self.log("Installing Your Plugin")
        # Add installation logic here
        return True
    
    def uninstall(self):
        """Uninstall the plugin"""
        self.log("Uninstalling Your Plugin")
        # Add cleanup logic here
        return True
    
    def get_urls(self):
        """Return URL patterns"""
        return [
            path('your-plugin/', self.your_view, name='your_plugin_view'),
        ]
    
    def your_view(self, request):
        """Your plugin view"""
        return render(request, 'your_plugin/your_template.html', {
            'message': 'Hello from your plugin!'
        })
```

### 3. Templates

```html
<!-- plugins/your_plugin/templates/your_plugin/your_template.html -->
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1>{{ message }}</h1>
</div>
{% endblock %}
```

## Plugin Features

### Navigation Integration

```python
def get_navigation_items(self, request):
    """Add items to the main navigation"""
    if request.user.is_authenticated:
        return [
            {
                'name': 'Your Plugin',
                'url': '/your-plugin/',
                'icon': 'star',
                'order': 100,
            }
        ]
    return []
```

### Dashboard Widgets

```python
def get_dashboard_widgets(self, request):
    """Add widgets to the dashboard"""
    if request.user.is_authenticated:
        return [
            {
                'name': 'Your Widget',
                'template': 'your_plugin/widget.html',
                'context': {'data': 'your data'},
                'order': 1,
            }
        ]
    return []
```

### API Endpoints

```python
def get_api_urls(self):
    """Return API URL patterns"""
    return [
        path('api/your-plugin/', self.api_view, name='your_plugin_api'),
    ]

def api_view(self, request):
    """API endpoint"""
    return self.json_response({
        'status': 'success',
        'data': 'your api data'
    })
```

### Settings Form

```python
def get_settings_form(self):
    """Return settings form"""
    from django import forms
    
    class YourPluginSettingsForm(forms.Form):
        api_key = forms.CharField(
            max_length=100,
            required=False,
            help_text="Your API key"
        )
        enabled = forms.BooleanField(
            required=False,
            help_text="Enable plugin features"
        )
    
    return YourPluginSettingsForm
```

### Dependencies

```python
def get_dependencies(self):
    """Return other plugins this plugin depends on"""
    return ['other_plugin_name']

def get_requirements(self):
    """Return additional Python requirements"""
    return [
        'requests>=2.25.0',
        'python-dateutil>=2.8.0',
    ]
```

## Plugin Management

### Command Line Interface

```bash
# List all plugins
python manage.py manage_plugins list

# Install a plugin
python manage.py manage_plugins install example_plugin

# Uninstall a plugin
python manage.py manage_plugins uninstall example_plugin

# Enable a plugin
python manage.py manage_plugins enable example_plugin

# Disable a plugin
python manage.py manage_plugins disable example_plugin

# Update a plugin
python manage.py manage_plugins update example_plugin

# Show plugin information
python manage.py manage_plugins info example_plugin
```

### Plugin Hooks

```python
# Register a hook
from plugins import register_plugin_hook

def my_hook_function(data):
    # Your hook logic here
    return processed_data

register_plugin_hook('on_chart_generated', my_hook_function)

# Execute hooks
from plugins import execute_plugin_hook

results = execute_plugin_hook('on_chart_generated', chart_data)
```

### Available Hooks

- `on_user_login`: Called when a user logs in
- `on_user_logout`: Called when a user logs out
- `on_chart_generated`: Called when a chart is generated
- `on_profile_updated`: Called when a user profile is updated
- `before_template_render`: Called before template rendering
- `after_template_render`: Called after template rendering
- `on_api_request`: Called on API requests
- `on_api_response`: Called on API responses

## Docker Integration

### Plugin Development with Docker

1. **Mount Plugin Directory**: Mount the plugins directory in your Docker setup:

```yaml
# docker-compose.yml
services:
  web:
    volumes:
      - .:/app
      - ./plugins:/app/plugins  # Mount plugins directory
```

2. **Plugin Requirements**: Add plugin requirements to your requirements.txt:

```txt
# requirements.txt
# Core requirements
Django>=4.2,<5.0
# ... other requirements

# Plugin requirements will be automatically added
```

3. **Plugin Discovery**: The plugin system automatically discovers plugins in the mounted directory.

### Team Development Workflow

1. **Create Feature Branch**: Each team member works on their own feature branch
2. **Develop Plugin**: Create and develop your plugin in the `plugins/` directory
3. **Test Locally**: Test your plugin with Docker
4. **Submit PR**: Submit a pull request with your plugin
5. **Code Review**: Team reviews the plugin
6. **Merge**: Plugin is merged into main branch
7. **Deploy**: Plugin is automatically deployed with the main application

## Best Practices

### Plugin Development

1. **Follow Naming Conventions**: Use lowercase with underscores for plugin names
2. **Documentation**: Include comprehensive documentation for your plugin
3. **Error Handling**: Implement proper error handling in your plugin
4. **Testing**: Write tests for your plugin functionality
5. **Security**: Follow security best practices
6. **Performance**: Optimize your plugin for performance

### Plugin Structure

```
your_plugin/
├── __init__.py              # Plugin entry point
├── plugin.py                # Main plugin class
├── models.py                # Database models (if needed)
├── views.py                 # View functions (if needed)
├── urls.py                  # URL patterns (if needed)
├── forms.py                 # Forms (if needed)
├── admin.py                 # Admin interface (if needed)
├── tests.py                 # Tests
├── migrations/              # Database migrations
├── templates/               # Templates
│   └── your_plugin/
├── static/                  # Static files
│   └── your_plugin/
│       ├── css/
│       ├── js/
│       └── img/
├── README.md                # Plugin documentation
└── requirements.txt         # Plugin-specific requirements
```

### Configuration

```python
# settings.py
PLUGIN_SETTINGS = {
    'auto_discover': True,
    'auto_install': False,
    'plugin_dir': 'plugins',
    'enabled_plugins': ['example_plugin'],
    'disabled_plugins': [],
    
    # Plugin-specific settings
    'your_plugin': {
        'api_key': 'your-api-key',
        'enabled': True,
        'debug': False,
    }
}
```

## Example Plugins

### 1. Chart Export Plugin

```python
class ChartExportPlugin(BasePlugin):
    name = "Chart Export"
    version = "1.0.0"
    description = "Export charts to PDF and images"
    
    def get_urls(self):
        return [
            path('export/pdf/<uuid:chart_id>/', self.export_pdf, name='export_pdf'),
            path('export/image/<uuid:chart_id>/', self.export_image, name='export_image'),
        ]
```

### 2. Social Sharing Plugin

```python
class SocialSharingPlugin(BasePlugin):
    name = "Social Sharing"
    version = "1.0.0"
    description = "Share charts on social media"
    
    def get_navigation_items(self, request):
        return [
            {
                'name': 'Share Chart',
                'url': '/share/',
                'icon': 'share',
                'order': 50,
            }
        ]
```

### 3. Advanced Analytics Plugin

```python
class AnalyticsPlugin(BasePlugin):
    name = "Advanced Analytics"
    version = "1.0.0"
    description = "Advanced chart analytics and insights"
    
    def get_dashboard_widgets(self, request):
        return [
            {
                'name': 'Chart Analytics',
                'template': 'analytics/widget.html',
                'context': self.get_analytics_data(request),
                'order': 1,
            }
        ]
```

## Troubleshooting

### Common Issues

1. **Plugin Not Loading**: Check that the plugin directory exists and has `__init__.py`
2. **Import Errors**: Ensure all dependencies are installed
3. **Template Not Found**: Check template directory structure
4. **URL Conflicts**: Ensure plugin URLs don't conflict with main app URLs

### Debugging

```python
# Enable plugin debugging
PLUGIN_SETTINGS = {
    'debug': True,
    'log_level': 'DEBUG',
}
```

### Logging

```python
# Plugin logging
self.log("Plugin message", level='info')
self.log("Error message", level='error')
self.log("Debug message", level='debug')
```

## Support

For questions or issues with the plugin system:

1. Check the example plugin for reference
2. Review the base plugin class documentation
3. Check the plugin management commands
4. Contact the development team

## Contributing

When contributing plugins:

1. Follow the established plugin structure
2. Include comprehensive documentation
3. Write tests for your plugin
4. Follow the team's coding standards
5. Test thoroughly before submitting 