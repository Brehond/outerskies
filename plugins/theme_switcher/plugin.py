from plugins.base import BasePlugin
from django.urls import path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json
import logging

logger = logging.getLogger(__name__)


class ThemeSwitcherPlugin(BasePlugin):
    name = "Theme Switcher"
    version = "1.0.0"
    description = "Dynamic theme switching with multiple color schemes"
    author = "Outer Skies Team"
    website = "https://outer-skies.com"

    requires_auth = False
    admin_enabled = True
    api_enabled = True

    # Themes are now managed by the theme_context processor.
    # This list is kept for reference but is no longer the source of truth.
    THEMES = {}

    DEFAULT_THEME = 'woh_pal1'

    def install(self):
        """Install the theme switcher plugin"""
        self.log("Installing Theme Switcher Plugin")
        # Add any installation logic here (e.g., creating default user preferences)
        return True

    def uninstall(self):
        """Uninstall the theme switcher plugin"""
        self.log("Uninstalling Theme Switcher Plugin")
        # Add cleanup logic here
        return True

    def get_urls(self):
        """Return URL patterns for the theme switcher"""
        return [
            path('theme/', self.theme_switcher_view, name='theme_switcher'),
            path('theme/switch/', self.switch_theme, name='switch_theme'),
        ]

    def get_navigation_items(self, request):
        """Add theme switcher to navigation"""
        return [
            {
                'name': 'Theme Switcher',
                'url': '/theme/',
                'icon': 'palette',
                'order': 1000,
            }
        ]

    def get_dashboard_widgets(self, request):
        """Add theme widget to dashboard"""
        return []  # Disabling dashboard widget as it's now in the header

    def get_api_urls(self):
        """Return API URL patterns"""
        return [
            path('api/theme/', self.api_theme_info, name='api_theme_info'),
            path('api/theme/switch/', self.api_switch_theme, name='api_switch_theme'),
        ]

    def get_settings_form(self):
        """Return settings form for theme preferences"""
        return None  # Disabling settings form for now

    def get_user_theme(self, request):
        """Get the current user's theme preference"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Get from user preferences (you can extend the User model or use a separate model)
            # For now, we'll use session storage
            return request.session.get('user_theme', self.DEFAULT_THEME)
        return request.session.get('user_theme', self.DEFAULT_THEME)

    def set_user_theme(self, request, theme_name):
        """Set the user's theme preference"""
        # Since themes are dynamic, we don't validate against a fixed list here.
        request.session['user_theme'] = theme_name
        return True

    def theme_switcher_view(self, request):
        """Main theme switcher view"""
        # This view is now less important as the switcher is in the header,
        # but we can keep it as a dedicated theme gallery page.
        return render(request, 'theme_switcher/theme_switcher.html')

    def switch_theme(self, request):
        """Switch user theme"""
        # Check if this is a POST request
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

        try:
            data = json.loads(request.body)
            theme_name = data.get('theme')

            if self.set_user_theme(request, theme_name):
                return JsonResponse({'success': True, 'theme': theme_name})
            else:
                return JsonResponse({'success': False, 'error': 'Invalid theme'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Theme switch error: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Internal error'}, status=500)

    def preview_theme(self, request, theme_name):
        """Preview a theme"""
        if theme_name not in self.THEMES:
            return redirect('theme_switcher')

        # Temporarily set the theme for this session
        request.session['preview_theme'] = theme_name
        return render(request, 'theme_switcher/preview.html', {
            'theme_name': theme_name,
            'theme_info': self.THEMES[theme_name]
        })

    def api_theme_info(self, request):
        """API endpoint to get theme information"""
        current_theme = self.get_user_theme(request)
        return JsonResponse({
            'current_theme': current_theme,
            'themes': self.THEMES,
            'theme_info': self.THEMES.get(current_theme, self.THEMES[self.DEFAULT_THEME])
        })

    def api_switch_theme(self, request):
        """API endpoint to switch theme"""
        # Check if this is a POST request
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

        return self.switch_theme(request)
