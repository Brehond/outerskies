# Theme Switcher Plugin

A comprehensive theme switching system for Outer Skies that allows users to choose from multiple beautiful color themes and easily add new ones.

## Features

- 🌌 **8 Pre-built Themes**: From cosmic night to light mode
- 🎨 **Easy Theme Addition**: Simple configuration to add new themes
- 🔄 **Real-time Switching**: Instant theme changes without page reload
- 📱 **Responsive Design**: Works perfectly on all devices
- 💾 **Session Persistence**: Remembers user's theme preference
- 🎯 **Dropdown Menu**: Quick theme switching from any page
- 👀 **Theme Preview**: Preview themes before applying
- 📊 **Dashboard Widget**: Current theme display with quick actions

## Available Themes

1. **Cosmic Night** - Deep space theme with purple and gold accents
2. **Sunset Orange** - Warm sunset theme with orange and red tones
3. **Ocean Deep** - Deep ocean theme with blue and teal accents
4. **Forest Green** - Natural forest theme with green and brown tones
5. **Rose Gold** - Elegant rose gold theme with pink and gold accents
6. **Midnight Purple** - Deep purple theme with mystical vibes
7. **Classic Dark** - Traditional dark theme with gray tones
8. **Light Mode** - Clean light theme for daytime use

## Installation

1. The plugin is automatically installed when the Django app starts
2. Access the theme switcher at `/theme/`
3. Use the dropdown menu in the top-right corner for quick switching

## Adding New Themes

To add a new theme, simply add it to the `THEMES` dictionary in `plugin.py`:

```python
'your_theme_name': {
    'name': 'Your Theme Name',
    'description': 'Description of your theme',
    'colors': {
        'primary': '#your_primary_color',
        'secondary': '#your_secondary_color',
        'accent': '#your_accent_color',
        'accent-secondary': '#your_accent_secondary_color',
        'text-primary': '#your_text_primary_color',
        'text-secondary': '#your_text_secondary_color',
        'text-muted': '#your_text_muted_color',
        'border': '#your_border_color',
        'border-light': '#your_border_light_color',
        'success': '#your_success_color',
        'error': '#your_error_color',
        'warning': '#your_warning_color',
        'info': '#your_info_color'
    }
}
```

## Usage

### For Users

1. **Quick Switch**: Use the dropdown menu in the top-right corner
2. **Full Theme Switcher**: Visit `/theme/` for the complete theme gallery
3. **Preview Themes**: Click "Preview" to see themes before applying
4. **Dashboard Widget**: View current theme and quick switch options

### For Developers

#### Including the Theme Dropdown

Add this to your base template:

```html
{% include 'theme_switcher/dropdown.html' with themes=themes current_theme=current_theme %}
```

#### Using Theme CSS Variables

The plugin provides CSS custom properties that you can use in your styles:

```css
.my-element {
    background-color: var(--primary-color);
    color: var(--text-primary-color);
    border: 1px solid var(--border-color);
}
```

#### JavaScript API

```javascript
// Get current theme
const currentTheme = window.themeSwitcher.getCurrentTheme();

// Switch theme
window.themeSwitcher.switchTheme('cosmic_night');

// Get theme data
const themeData = window.themeSwitcher.getThemeData('ocean_deep');
```

## File Structure

```
plugins/theme_switcher/
├── __init__.py                 # Plugin initialization
├── plugin.py                   # Main plugin class
├── README.md                   # This file
├── templates/
│   └── theme_switcher/
│       ├── theme_switcher.html # Main theme switcher page
│       ├── dropdown.html       # Theme dropdown component
│       ├── preview.html        # Theme preview page
│       └── widget.html         # Dashboard widget
└── static/
    └── theme_switcher/
        ├── css/
        │   └── themes.css      # Theme CSS variables
        └── js/
            └── theme-switcher.js # Theme switching JavaScript
```

## API Endpoints

- `GET /theme/` - Main theme switcher page
- `POST /theme/switch/` - Switch user theme
- `GET /theme/preview/<theme_name>/` - Preview specific theme
- `GET /api/theme/` - Get theme information
- `POST /api/theme/switch/` - API endpoint for switching themes

## Configuration

The plugin supports several configuration options through the settings form:

- **Default Theme**: Set the default theme for new users
- **Allow User Override**: Enable/disable user theme changes
- **Show Theme Switcher**: Control visibility of theme switcher in navigation

## Browser Support

- Chrome 49+
- Firefox 52+
- Safari 10+
- Edge 79+

## Contributing

To add new themes or improve the plugin:

1. Add your theme to the `THEMES` dictionary
2. Test the theme across different pages
3. Ensure good contrast ratios for accessibility
4. Update this README with theme information

## License

This plugin is part of the Outer Skies project and follows the same license terms. 