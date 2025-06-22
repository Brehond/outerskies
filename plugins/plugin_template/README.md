# Plugin Template

## Description

This is a template for creating new plugins for the Outer Skies astrology application.

## Installation

1. Copy this entire directory and rename it to your plugin name
2. Update all references to "PluginTemplate" with your plugin name
3. Customize the plugin functionality
4. Install the plugin using the management command

## Usage

```bash
# Install the plugin
python manage.py manage_plugins install your_plugin_name

# Enable the plugin
python manage.py manage_plugins enable your_plugin_name

# Check plugin status
python manage.py manage_plugins info your_plugin_name
```

## Configuration

Add your plugin settings to `settings.py`:

```python
PLUGIN_SETTINGS = {
    'your_plugin_name': {
        'enabled': True,
        'api_key': 'your-api-key',
        # Add other settings as needed
    }
}
```

## Features

- [ ] Add your features here
- [ ] List what your plugin does
- [ ] Document any special requirements

## Dependencies

- List any Python packages your plugin requires
- List any other plugins your plugin depends on

## Development

1. Follow the plugin development guidelines
2. Test your plugin thoroughly
3. Document your code
4. Submit a pull request

## Support

For questions or issues, contact the development team. 