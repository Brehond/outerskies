"""
Rate Limiting Middleware

Focused middleware for handling rate limiting with configurable limits per endpoint type.
"""

import time
import logging
from typing import Optional
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security_audit')


class RateLimitMiddleware(MiddlewareMixin):
    """
    Focused rate limiting middleware with configurable limits per endpoint type.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        
        # Rate limiting configuration
        self.rate_limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'api': {'requests': 1000, 'window': 3600},     # 1000 API requests per hour
            'chart_generation': {'requests': 10, 'window': 3600},  # 10 charts per hour
            'auth': {'requests': 5, 'window': 300},        # 5 auth attempts per 5 minutes
            'file_upload': {'requests': 20, 'window': 3600},  # 20 uploads per hour
        }
    
    def process_request(self, request):
        """Check rate limiting rules."""
        # Skip for static files and health checks
        if self._should_skip_rate_limit(request):
            return None
            
        client_ip = self._get_client_ip(request)
        rate_limit_type = self._get_rate_limit_type(request)
        
        # Check rate limit
        if self._is_rate_limited(client_ip, rate_limit_type):
            logger.warning(f'Rate limit exceeded for IP: {client_ip}, type: {rate_limit_type}')
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Too many requests for {rate_limit_type}',
                'retry_after': self._get_retry_after(client_ip, rate_limit_type)
            }, status=429)
        
        return None
    
    def _should_skip_rate_limit(self, request) -> bool:
        """Determine if rate limiting should be skipped."""
        skip_paths = [
            '/static/', '/media/', '/favicon.ico',
            '/api/v1/system/health/', '/api/v1/system/quick-health/'
        ]
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    def _get_rate_limit_type(self, request) -> str:
        """Determine rate limit type based on request path."""
        path = request.path.lower()
        
        if '/auth/' in path:
            return 'auth'
        elif '/chart/' in path and request.method == 'POST':
            return 'chart_generation'
        elif '/upload/' in path or request.content_type == 'multipart/form-data':
            return 'file_upload'
        elif path.startswith('/api/'):
            return 'api'
        else:
            return 'default'
    
    def _is_rate_limited(self, client_ip: str, rate_limit_type: str) -> bool:
        """Check if client is rate limited."""
        limit_config = self.rate_limits.get(rate_limit_type, self.rate_limits['default'])
        max_requests = limit_config['requests']
        window = limit_config['window']
        
        # Create cache key
        cache_key = f'rate_limit:{client_ip}:{rate_limit_type}'
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= max_requests:
            return True
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        return False
    
    def _get_retry_after(self, client_ip: str, rate_limit_type: str) -> int:
        """Get retry after time in seconds."""
        limit_config = self.rate_limits.get(rate_limit_type, self.rate_limits['default'])
        return limit_config['window'] 