import time
import logging
import psutil
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.conf import settings

logger = logging.getLogger('security')

class RateLimitMiddleware:
    """
    Middleware for handling rate limiting and resource monitoring:
    - Per-IP rate limiting
    - Concurrent request limiting
    - Memory usage monitoring
    - Request queuing
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limiting settings
        self.requests_per_minute = getattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE', 60)
        self.max_concurrent_requests = getattr(settings, 'MAX_CONCURRENT_REQUESTS', 5)
        self.memory_threshold = getattr(settings, 'MEMORY_USAGE_THRESHOLD', 90)
        self.queue_timeout = getattr(settings, 'RATE_LIMIT_QUEUE_TIMEOUT', 30)
        
    def __call__(self, request):
        # Skip rate limiting for static/media files and test requests
        if request.path.startswith(('/static/', '/media/')) or settings.DEBUG:
            return self.get_response(request)
            
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JsonResponse({'error': 'Rate limit exceeded'}, status=429)
            
        # Check concurrent requests
        if not self._check_concurrent_requests(client_ip):
            logger.warning(f"Too many concurrent requests from IP: {client_ip}")
            return JsonResponse({'error': 'Too many concurrent requests'}, status=429)
            
        # Check memory usage
        if self._check_memory_usage():
            logger.warning("High memory usage detected")
            # Could implement request queuing here
            return JsonResponse({'error': 'Server is busy'}, status=429)
            
        try:
            response = self.get_response(request)
            return response
        finally:
            # Clean up rate limiting data
            self._cleanup_rate_limit(client_ip)
            
    def _get_client_ip(self, request):
        """Get client IP address, handling proxy headers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
        
    def _check_rate_limit(self, client_ip):
        """Check if the client has exceeded their rate limit."""
        key = f'rate_limit_{client_ip}'
        current_time = int(time.time())
        
        # Get current request count
        request_data = cache.get(key, {'count': 0, 'window_start': current_time})
        
        # Reset counter if window has expired
        if current_time - request_data['window_start'] >= 60:
            request_data = {'count': 0, 'window_start': current_time}
            
        # Increment counter
        request_data['count'] += 1
        cache.set(key, request_data, 60)  # Cache for 1 minute
        
        return request_data['count'] <= self.requests_per_minute
        
    def _check_concurrent_requests(self, client_ip):
        """Check if the client has too many concurrent requests."""
        key = f'concurrent_requests_{client_ip}'
        current_requests = cache.get(key, 0)
        
        if current_requests >= self.max_concurrent_requests:
            return False
            
        # Increment counter
        cache.set(key, current_requests + 1, 30)  # Cache for 30 seconds
        return True
        
    def _check_memory_usage(self):
        """Check if memory usage exceeds threshold."""
        try:
            memory_percent = psutil.Process().memory_percent()
            return memory_percent > self.memory_threshold
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # If we can't get memory info, assume it's fine
            return False
        
    def _cleanup_rate_limit(self, client_ip):
        """Clean up rate limiting data for a client."""
        key = f'concurrent_requests_{client_ip}'
        current = cache.get(key, 0)
        if current > 0:
            cache.set(key, current - 1, 30)
            
    def get_rate_limit_status(self, client_ip):
        """Get current rate limit status for a client."""
        key = f'rate_limit_{client_ip}'
        request_data = cache.get(key, {'count': 0, 'window_start': int(time.time())})
        
        return {
            'requests_remaining': max(0, self.requests_per_minute - request_data['count']),
            'window_reset': request_data['window_start'] + 60 - int(time.time()),
            'concurrent_requests': cache.get(f'concurrent_requests_{client_ip}', 0)
        } 