"""
Comprehensive API Versioning System

This module provides consistent API versioning with:
- URL path versioning
- Version deprecation handling
- Backward compatibility
- Version-specific features
- Migration guides
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from django.http import JsonResponse
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from datetime import datetime, timedelta

logger = logging.getLogger('api_versioning')


class APIVersion:
    """
    API version configuration and management.
    """
    
    # Supported API versions
    SUPPORTED_VERSIONS = ['v1']
    
    # Current stable version
    CURRENT_VERSION = 'v1'
    
    # Deprecated versions with deprecation dates
    DEPRECATED_VERSIONS = {
        # 'v0': {
        #     'deprecated_date': '2024-01-01',
        #     'sunset_date': '2024-12-31',
        #     'migration_guide': 'https://docs.example.com/migrate-v0-to-v1'
        # }
    }
    
    # Version-specific features
    VERSION_FEATURES = {
        'v1': {
            'chart_generation': True,
            'ai_interpretation': True,
            'user_management': True,
            'subscription_management': True,
            'file_upload': True,
            'chat_system': True,
            'theme_system': True,
            'rate_limiting': True,
            'webhooks': False,  # Coming in v2
            'batch_operations': False,  # Coming in v2
            'real_time_updates': False,  # Coming in v2
        }
    }
    
    # Version-specific rate limits
    VERSION_RATE_LIMITS = {
        'v1': {
            'default': {'requests': 100, 'window': 3600},
            'api': {'requests': 1000, 'window': 3600},
            'chart_generation': {'requests': 10, 'window': 3600},
            'ai_interpretation': {'requests': 50, 'window': 3600},
        }
    }
    
    @classmethod
    def get_supported_versions(cls) -> List[str]:
        """Get list of supported API versions."""
        return cls.SUPPORTED_VERSIONS.copy()
    
    @classmethod
    def is_supported(cls, version: str) -> bool:
        """Check if version is supported."""
        return version in cls.SUPPORTED_VERSIONS
    
    @classmethod
    def is_deprecated(cls, version: str) -> bool:
        """Check if version is deprecated."""
        return version in cls.DEPRECATED_VERSIONS
    
    @classmethod
    def is_sunset(cls, version: str) -> bool:
        """Check if version has been sunset."""
        if version not in cls.DEPRECATED_VERSIONS:
            return False
        
        sunset_date = cls.DEPRECATED_VERSIONS[version]['sunset_date']
        sunset_datetime = datetime.strptime(sunset_date, '%Y-%m-%d')
        return datetime.now() > sunset_datetime
    
    @classmethod
    def get_deprecation_info(cls, version: str) -> Optional[Dict[str, Any]]:
        """Get deprecation information for a version."""
        if version not in cls.DEPRECATED_VERSIONS:
            return None
        
        deprecation_info = cls.DEPRECATED_VERSIONS[version].copy()
        
        # Calculate days until sunset
        sunset_date = datetime.strptime(deprecation_info['sunset_date'], '%Y-%m-%d')
        days_until_sunset = (sunset_date - datetime.now()).days
        
        deprecation_info['days_until_sunset'] = max(0, days_until_sunset)
        deprecation_info['is_sunset'] = days_until_sunset <= 0
        
        return deprecation_info
    
    @classmethod
    def get_version_features(cls, version: str) -> Dict[str, Any]:
        """Get features available in a specific version."""
        return cls.VERSION_FEATURES.get(version, {}).copy()
    
    @classmethod
    def get_version_rate_limits(cls, version: str) -> Dict[str, Any]:
        """Get rate limits for a specific version."""
        return cls.VERSION_RATE_LIMITS.get(version, {}).copy()
    
    @classmethod
    def is_feature_available(cls, version: str, feature: str) -> bool:
        """Check if a feature is available in a specific version."""
        features = cls.get_version_features(version)
        return features.get(feature, False)


class APIVersionMiddleware:
    """
    Middleware for handling API versioning.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract version from URL path
        version = self._extract_version_from_path(request.path)
        
        if version:
            # Store version in request
            request.api_version = version
            
            # Check if version is supported
            if not APIVersion.is_supported(version):
                return JsonResponse({
                    'error': 'Unsupported API version',
                    'message': f'API version {version} is not supported',
                    'supported_versions': APIVersion.get_supported_versions(),
                    'current_version': APIVersion.CURRENT_VERSION
                }, status=400)
            
            # Check if version is sunset
            if APIVersion.is_sunset(version):
                return JsonResponse({
                    'error': 'API version sunset',
                    'message': f'API version {version} has been sunset and is no longer available',
                    'supported_versions': APIVersion.get_supported_versions(),
                    'current_version': APIVersion.CURRENT_VERSION
                }, status=410)
        
        response = self.get_response(request)
        
        # Add version headers
        if hasattr(request, 'api_version'):
            self._add_version_headers(response, request.api_version)
        
        return response
    
    def _extract_version_from_path(self, path: str) -> Optional[str]:
        """Extract API version from URL path."""
        if path.startswith('/api/'):
            parts = path.split('/')
            if len(parts) >= 3 and parts[1] == 'api':
                version = parts[2]
                if version.startswith('v') and version[1:].isdigit():
                    return version
        return None
    
    def _add_version_headers(self, response, version: str):
        """Add version-related headers to response."""
        response['X-API-Version'] = version
        response['X-API-Current-Version'] = APIVersion.CURRENT_VERSION
        
        # Add deprecation headers if version is deprecated
        if APIVersion.is_deprecated(version):
            deprecation_info = APIVersion.get_deprecation_info(version)
            if deprecation_info:
                response['X-API-Deprecated'] = 'true'
                response['X-API-Deprecated-Date'] = deprecation_info['deprecated_date']
                response['X-API-Sunset-Date'] = deprecation_info['sunset_date']
                response['X-API-Migration-Guide'] = deprecation_info['migration_guide']
                
                if deprecation_info['days_until_sunset'] > 0:
                    response['X-API-Days-Until-Sunset'] = str(deprecation_info['days_until_sunset'])


def require_api_version(versions: List[str] = None):
    """
    Decorator to require specific API versions for a view.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Get API version from request
            version = getattr(request, 'api_version', None)
            
            if not version:
                return JsonResponse({
                    'error': 'API version required',
                    'message': 'API version must be specified in URL path (e.g., /api/v1/...)',
                    'supported_versions': APIVersion.get_supported_versions()
                }, status=400)
            
            # Check if version is in required versions
            if versions and version not in versions:
                return JsonResponse({
                    'error': 'Unsupported API version',
                    'message': f'This endpoint requires one of the following versions: {", ".join(versions)}',
                    'requested_version': version,
                    'required_versions': versions
                }, status=400)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_feature(feature: str):
    """
    Decorator to require a specific feature for a view.
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Get API version from request
            version = getattr(request, 'api_version', None)
            
            if not version:
                return JsonResponse({
                    'error': 'API version required',
                    'message': 'API version must be specified in URL path'
                }, status=400)
            
            # Check if feature is available in this version
            if not APIVersion.is_feature_available(version, feature):
                return JsonResponse({
                    'error': 'Feature not available',
                    'message': f'Feature "{feature}" is not available in API version {version}',
                    'available_features': APIVersion.get_version_features(version),
                    'current_version': version
                }, status=400)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class VersionedAPIView(APIView):
    """
    Base class for versioned API views.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.version = None
    
    def dispatch(self, request, *args, **kwargs):
        # Get version from request
        self.version = getattr(request, 'api_version', None)
        
        # Validate version
        if not self.version:
            return JsonResponse({
                'error': 'API version required',
                'message': 'API version must be specified in URL path'
            }, status=400)
        
        if not APIVersion.is_supported(self.version):
            return JsonResponse({
                'error': 'Unsupported API version',
                'message': f'API version {self.version} is not supported'
            }, status=400)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_version_features(self) -> Dict[str, Any]:
        """Get features available in current version."""
        return APIVersion.get_version_features(self.version)
    
    def is_feature_available(self, feature: str) -> bool:
        """Check if feature is available in current version."""
        return APIVersion.is_feature_available(self.version, feature)


# Utility functions
def get_api_version(request) -> Optional[str]:
    """Get API version from request."""
    return getattr(request, 'api_version', None)


def is_version_deprecated(version: str) -> bool:
    """Check if API version is deprecated."""
    return APIVersion.is_deprecated(version)


def get_deprecation_warning(version: str) -> Optional[str]:
    """Get deprecation warning message for a version."""
    if not APIVersion.is_deprecated(version):
        return None
    
    deprecation_info = APIVersion.get_deprecation_info(version)
    if not deprecation_info:
        return None
    
    if deprecation_info['is_sunset']:
        return f'API version {version} has been sunset and is no longer available'
    
    days_remaining = deprecation_info['days_until_sunset']
    if days_remaining <= 30:
        return f'API version {version} will be sunset in {days_remaining} days. Please migrate to {APIVersion.CURRENT_VERSION}.'
    else:
        return f'API version {version} is deprecated and will be sunset on {deprecation_info["sunset_date"]}. Please migrate to {APIVersion.CURRENT_VERSION}.'


def get_version_info(version: str) -> Dict[str, Any]:
    """Get comprehensive information about an API version."""
    return {
        'version': version,
        'is_supported': APIVersion.is_supported(version),
        'is_deprecated': APIVersion.is_deprecated(version),
        'is_sunset': APIVersion.is_sunset(version),
        'features': APIVersion.get_version_features(version),
        'rate_limits': APIVersion.get_version_rate_limits(version),
        'deprecation_info': APIVersion.get_deprecation_info(version),
        'current_version': APIVersion.CURRENT_VERSION,
        'supported_versions': APIVersion.get_supported_versions()
    }


# API endpoints for version management
@api_view(['GET'])
def api_versions(request):
    """Get information about all API versions."""
    versions_info = {}
    
    for version in APIVersion.get_supported_versions():
        versions_info[version] = get_version_info(version)
    
    return Response({
        'versions': versions_info,
        'current_version': APIVersion.CURRENT_VERSION,
        'supported_versions': APIVersion.get_supported_versions()
    })


@api_view(['GET'])
def api_version_info(request, version):
    """Get information about a specific API version."""
    if not APIVersion.is_supported(version):
        return Response({
            'error': 'Unsupported API version',
            'message': f'API version {version} is not supported'
        }, status=400)
    
    return Response(get_version_info(version))


@api_view(['GET'])
def api_migration_guide(request, from_version, to_version):
    """Get migration guide between API versions."""
    # This would typically return a migration guide from documentation
    return Response({
        'from_version': from_version,
        'to_version': to_version,
        'migration_guide_url': f'https://docs.example.com/migrate-{from_version}-to-{to_version}',
        'breaking_changes': [],
        'new_features': [],
        'deprecated_features': []
    }) 