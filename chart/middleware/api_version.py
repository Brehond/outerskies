import re
import logging
from django.http import HttpResponseBadRequest, JsonResponse
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('security')


class APIVersionMiddleware:
    """
    API versioning middleware that provides:
    - API version validation
    - Version deprecation handling
    - Version migration support
    - Version compatibility checks
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.current_version = getattr(settings, 'API_CURRENT_VERSION', '1.0')
        self.min_version = getattr(settings, 'API_MIN_VERSION', '1.0')
        self.max_version = getattr(settings, 'API_MAX_VERSION', '2.0')
        self.deprecated_versions = getattr(settings, 'API_DEPRECATED_VERSIONS', [])
        self.version_header = getattr(settings, 'API_VERSION_HEADER', 'X-API-Version')
        self.version_pattern = re.compile(r'^v?(\d+\.\d+)$')

    def __call__(self, request):
        # Skip version validation for non-API requests
        if not self._is_api_request(request):
            return self.get_response(request)

        # Skip version validation for public endpoints
        if self._is_public_endpoint(request):
            return self.get_response(request)

        # Get API version from header
        version = request.headers.get(self.version_header)

        # If no version provided, use current version for v1 API
        if not version and request.path.startswith('/api/v1/'):
            version = self.current_version

        # Check if version is provided
        if not version:
            return self._handle_missing_version(request)

        # Check if version is valid
        if not self._is_valid_version(version):
            return self._handle_invalid_version(request, version)

        # Check if version is compatible
        if not self._is_compatible_version(version):
            return self._handle_incompatible_version(request, version)

        # Check if version is deprecated
        if self._is_deprecated_version(version):
            return self._handle_deprecated_version(request, version)

        # Add version info to request
        request.api_version = version

        response = self.get_response(request)

        # Add version headers
        self._add_version_headers(response)

        return response

    def _is_api_request(self, request):
        """Check if request is an API request."""
        return request.path.startswith('/api/')

    def _is_public_endpoint(self, request):
        """Check if endpoint is public and should skip version validation."""
        public_paths = [
            '/api/health/',
            '/api/public/',
            '/api/docs/',
            '/api/v1/system/health/',
            '/api/v1/system/ai_models/',
            '/api/v1/system/themes/',
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/logout/',
        ]
        return any(request.path.startswith(path) for path in public_paths)

    def _is_valid_version(self, version):
        """Check if version is valid."""
        if not self.version_pattern.match(version):
            return False

        try:
            major, minor = map(int, version.split('.'))
            return major >= 0 and minor >= 0
        except ValueError:
            return False

    def _is_compatible_version(self, version):
        """Check if version is compatible."""
        try:
            requested = tuple(map(int, version.split('.')))
            minimum = tuple(map(int, self.min_version.split('.')))
            maximum = tuple(map(int, self.max_version.split('.')))
            return minimum <= requested <= maximum
        except ValueError:
            return False

    def _is_deprecated_version(self, version):
        """Check if version is deprecated."""
        return version in self.deprecated_versions

    def _handle_missing_version(self, request):
        """Handle missing version."""
        logger.warning(f'Missing API version from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'API version is required',
            'current_version': self.current_version,
            'min_version': self.min_version,
            'max_version': self.max_version
        }, status=400)

    def _handle_invalid_version(self, request, version):
        """Handle invalid version."""
        logger.warning(f'Invalid API version {version} from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Invalid API version',
            'current_version': self.current_version,
            'min_version': self.min_version,
            'max_version': self.max_version
        }, status=400)

    def _handle_incompatible_version(self, request, version):
        """Handle incompatible version."""
        logger.warning(f'Incompatible API version {version} from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Incompatible API version',
            'current_version': self.current_version,
            'min_version': self.min_version,
            'max_version': self.max_version
        }, status=400)

    def _handle_deprecated_version(self, request, version):
        """Handle deprecated version."""
        logger.warning(f'Deprecated API version {version} from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'API version is deprecated',
            'current_version': self.current_version,
            'min_version': self.min_version,
            'max_version': self.max_version,
            'deprecation_date': self._get_deprecation_date(version)
        }, status=400)

    def _add_version_headers(self, response):
        """Add version headers to response."""
        response['X-API-Current-Version'] = self.current_version
        response['X-API-Min-Version'] = self.min_version
        response['X-API-Max-Version'] = self.max_version

    def _get_deprecation_date(self, version):
        """Get deprecation date for version."""
        # This could be stored in settings or database
        return getattr(settings, f'API_DEPRECATION_DATE_{version.replace(".", "_")}', 'Unknown')
