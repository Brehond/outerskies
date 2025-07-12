import time
import logging
import psutil
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Middleware for handling security-related concerns:
    - Request size limits
    - Concurrent request limiting
    - Memory usage monitoring
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Maximum request size in bytes (default: 1MB)
        self.max_request_size = getattr(settings, 'MAX_REQUEST_SIZE', 1024 * 1024)
        # Maximum concurrent requests per IP
        self.max_concurrent_requests = getattr(settings, 'MAX_CONCURRENT_REQUESTS', 5)
        # Memory usage threshold (percentage)
        self.memory_threshold = getattr(settings, 'MEMORY_USAGE_THRESHOLD', 90)

    def __call__(self, request):
        # Skip middleware for static/media files
        if request.path.startswith(('/static/', '/media/')):
            return self.get_response(request)

        # Check request size
        if request.method == 'POST':
            content_length = request.META.get('CONTENT_LENGTH', 0)
            if int(content_length) > self.max_request_size:
                logger.warning(f"Request too large: {content_length} bytes from {request.META.get('REMOTE_ADDR')}")
                return HttpResponse('Request too large', status=413)

        # Check concurrent requests
        client_ip = self._get_client_ip(request)
        concurrent_key = f'concurrent_requests_{client_ip}'
        current_requests = cache.get(concurrent_key, 0)

        if current_requests >= self.max_concurrent_requests:
            logger.warning(f"Too many concurrent requests from {client_ip}")
            return HttpResponse('Too many concurrent requests', status=429)

        # Increment concurrent requests counter
        cache.set(concurrent_key, current_requests + 1, 30)  # 30 second expiry

        # Check memory usage
        if self._check_memory_usage():
            logger.warning("High memory usage detected")
            # Could implement rate limiting or request queuing here

        try:
            response = self.get_response(request)
            return response
        finally:
            # Decrement concurrent requests counter
            current = cache.get(concurrent_key, 0)
            if current > 0:
                cache.set(concurrent_key, current - 1, 30)

    def _get_client_ip(self, request):
        """Get client IP address, handling proxy headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def _check_memory_usage(self):
        """Check if memory usage exceeds threshold."""
        memory_percent = psutil.Process().memory_percent()
        return memory_percent > self.memory_threshold

    def get_concurrent_count(self, client_ip):
        """Get the current concurrent request count for an IP."""
        concurrent_key = f'concurrent_requests_{client_ip}'
        return cache.get(concurrent_key, 0)

    def increment_concurrent(self, client_ip):
        """Increment concurrent request count for an IP."""
        concurrent_key = f'concurrent_requests_{client_ip}'
        current = cache.get(concurrent_key, 0)
        cache.set(concurrent_key, current + 1, 30)
        return current + 1

    def decrement_concurrent(self, client_ip):
        """Decrement concurrent request count for an IP."""
        concurrent_key = f'concurrent_requests_{client_ip}'
        current = cache.get(concurrent_key, 0)
        if current > 0:
            cache.set(concurrent_key, current - 1, 30)
        return max(current - 1, 0)
