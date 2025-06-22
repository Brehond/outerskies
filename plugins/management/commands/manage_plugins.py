"""
Django management command for managing plugins
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from plugins import get_plugin_manager
import os
import sys

class Command(BaseCommand):
    help = 'Manage Outer Skies plugins'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['list', 'install', 'uninstall', 'enable', 'disable', 'update', 'info'],
            help='Action to perform on plugins'
        )
        parser.add_argument(
            'plugin_name',
            nargs='?',
            help='Name of the plugin to manage'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force the action without confirmation'
        )

    def handle(self, *args, **options):
        action = options['action']
        plugin_name = options['plugin_name']
        force = options['force']

        plugin_manager = get_plugin_manager()

        if action == 'list':
            self.list_plugins(plugin_manager)
        elif action == 'install':
            if not plugin_name:
                raise CommandError('Plugin name is required for install action')
            self.install_plugin(plugin_manager, plugin_name, force)
        elif action == 'uninstall':
            if not plugin_name:
                raise CommandError('Plugin name is required for uninstall action')
            self.uninstall_plugin(plugin_manager, plugin_name, force)
        elif action == 'enable':
            if not plugin_name:
                raise CommandError('Plugin name is required for enable action')
            self.enable_plugin(plugin_manager, plugin_name)
        elif action == 'disable':
            if not plugin_name:
                raise CommandError('Plugin name is required for disable action')
            self.disable_plugin(plugin_manager, plugin_name)
        elif action == 'update':
            if not plugin_name:
                raise CommandError('Plugin name is required for update action')
            self.update_plugin(plugin_manager, plugin_name, force)
        elif action == 'info':
            if not plugin_name:
                raise CommandError('Plugin name is required for info action')
            self.show_plugin_info(plugin_manager, plugin_name)

    def list_plugins(self, plugin_manager):
        """List all available plugins"""
        self.stdout.write(self.style.SUCCESS('Available Plugins:'))
        self.stdout.write('=' * 50)
        
        # Discover plugins first
        plugin_manager.discover_plugins()
        
        plugins = plugin_manager.get_all_plugins()
        if not plugins:
            self.stdout.write(self.style.WARNING('No plugins found'))
            return
        
        for name, plugin in plugins.items():
            info = plugin.get_plugin_info()
            status = '✅ Active' if name in plugin_manager.registered_plugins else '❌ Inactive'
            
            self.stdout.write(f"\n{self.style.SUCCESS(name)} - {status}")
            self.stdout.write(f"  Version: {info['version']}")
            self.stdout.write(f"  Description: {info['description']}")
            self.stdout.write(f"  Author: {info['author']}")
            self.stdout.write(f"  Requires Auth: {info['requires_auth']}")
            self.stdout.write(f"  Admin Enabled: {info['admin_enabled']}")
            self.stdout.write(f"  API Enabled: {info['api_enabled']}")

    def install_plugin(self, plugin_manager, plugin_name, force):
        """Install a plugin"""
        self.stdout.write(f"Installing plugin: {plugin_name}")
        
        try:
            plugin = plugin_manager.get_plugin(plugin_name)
            if not plugin:
                # Try to register the plugin first
                plugin_manager.register_plugin(plugin_name)
                plugin = plugin_manager.get_plugin(plugin_name)
            
            if not plugin:
                raise CommandError(f"Plugin '{plugin_name}' not found")
            
            # Check dependencies
            dependencies = plugin.get_dependencies()
            if dependencies:
                self.stdout.write(f"Checking dependencies: {', '.join(dependencies)}")
                for dep in dependencies:
                    if not plugin_manager.get_plugin(dep):
                        raise CommandError(f"Dependency '{dep}' not found")
            
            # Install the plugin
            if plugin.install():
                self.stdout.write(self.style.SUCCESS(f"✅ Plugin '{plugin_name}' installed successfully"))
            else:
                raise CommandError(f"Failed to install plugin '{plugin_name}'")
                
        except Exception as e:
            raise CommandError(f"Error installing plugin '{plugin_name}': {e}")

    def uninstall_plugin(self, plugin_manager, plugin_name, force):
        """Uninstall a plugin"""
        if not force:
            confirm = input(f"Are you sure you want to uninstall '{plugin_name}'? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write("Uninstall cancelled")
                return
        
        self.stdout.write(f"Uninstalling plugin: {plugin_name}")
        
        try:
            plugin = plugin_manager.get_plugin(plugin_name)
            if not plugin:
                raise CommandError(f"Plugin '{plugin_name}' not found")
            
            if plugin.uninstall():
                self.stdout.write(self.style.SUCCESS(f"✅ Plugin '{plugin_name}' uninstalled successfully"))
            else:
                raise CommandError(f"Failed to uninstall plugin '{plugin_name}'")
                
        except Exception as e:
            raise CommandError(f"Error uninstalling plugin '{plugin_name}': {e}")

    def enable_plugin(self, plugin_manager, plugin_name):
        """Enable a plugin"""
        self.stdout.write(f"Enabling plugin: {plugin_name}")
        
        try:
            plugin_manager.register_plugin(plugin_name)
            self.stdout.write(self.style.SUCCESS(f"✅ Plugin '{plugin_name}' enabled successfully"))
        except Exception as e:
            raise CommandError(f"Error enabling plugin '{plugin_name}': {e}")

    def disable_plugin(self, plugin_manager, plugin_name):
        """Disable a plugin"""
        self.stdout.write(f"Disabling plugin: {plugin_name}")
        
        try:
            if plugin_name in plugin_manager.registered_plugins:
                plugin_manager.registered_plugins.remove(plugin_name)
                if plugin_name in plugin_manager.plugins:
                    del plugin_manager.plugins[plugin_name]
                self.stdout.write(self.style.SUCCESS(f"✅ Plugin '{plugin_name}' disabled successfully"))
            else:
                self.stdout.write(self.style.WARNING(f"Plugin '{plugin_name}' was not enabled"))
        except Exception as e:
            raise CommandError(f"Error disabling plugin '{plugin_name}': {e}")

    def update_plugin(self, plugin_manager, plugin_name, force):
        """Update a plugin"""
        self.stdout.write(f"Updating plugin: {plugin_name}")
        
        try:
            # For now, just reinstall the plugin
            self.uninstall_plugin(plugin_manager, plugin_name, True)
            self.install_plugin(plugin_manager, plugin_name, True)
            self.stdout.write(self.style.SUCCESS(f"✅ Plugin '{plugin_name}' updated successfully"))
        except Exception as e:
            raise CommandError(f"Error updating plugin '{plugin_name}': {e}")

    def show_plugin_info(self, plugin_manager, plugin_name):
        """Show detailed information about a plugin"""
        try:
            plugin = plugin_manager.get_plugin(plugin_name)
            if not plugin:
                # Try to register the plugin first
                plugin_manager.register_plugin(plugin_name)
                plugin = plugin_manager.get_plugin(plugin_name)
            
            if not plugin:
                raise CommandError(f"Plugin '{plugin_name}' not found")
            
            info = plugin.get_plugin_info()
            
            self.stdout.write(self.style.SUCCESS(f"Plugin Information: {plugin_name}"))
            self.stdout.write('=' * 50)
            self.stdout.write(f"Name: {info['name']}")
            self.stdout.write(f"Version: {info['version']}")
            self.stdout.write(f"Description: {info['description']}")
            self.stdout.write(f"Author: {info['author']}")
            self.stdout.write(f"Website: {info['website']}")
            self.stdout.write(f"Requires Auth: {info['requires_auth']}")
            self.stdout.write(f"Admin Enabled: {info['admin_enabled']}")
            self.stdout.write(f"API Enabled: {info['api_enabled']}")
            
            # Show additional information
            requirements = plugin.get_requirements()
            if requirements:
                self.stdout.write(f"\nRequirements: {', '.join(requirements)}")
            
            dependencies = plugin.get_dependencies()
            if dependencies:
                self.stdout.write(f"Dependencies: {', '.join(dependencies)}")
            
            # Validate installation
            is_valid, message = plugin.validate_installation()
            self.stdout.write(f"Installation Status: {'✅ Valid' if is_valid else '❌ Invalid'}")
            self.stdout.write(f"Validation Message: {message}")
            
        except Exception as e:
            raise CommandError(f"Error showing plugin info for '{plugin_name}': {e}") 