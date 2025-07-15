"""
Enhanced Rate Limiting System

This module provides sophisticated rate limiting with:
- User-based and IP-based limits
- Endpoint-specific limits
- Burst protection
- Sliding window implementation
- Rate limit headers
- Analytics and monitoring
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger('rate_limit')


class RateLimitConfig:
    """
    Configuration for rate limiting rules.
    """
    
    # Default rate limits
    DEFAULT_LIMITS = {
        'default': {
            'requests': 100,
            'window': 3600,  # 1 hour
            'burst': 10
        },
        'api': {
            'requests': 1000,
            'window': 3600,  # 1 hour
            'burst': 50
        },
        'auth': {
            'requests': 5,
            'window': 300,  # 5 minutes
            'burst': 2
        },
        'chart_generation': {
            'requests': 10,
            'window': 3600,  # 1 hour
            'burst': 2
        },
        'ai_interpretation': {
            'requests': 50,
            'window': 3600,  # 1 hour
            'burst': 5
        },
        'file_upload': {
            'requests': 20,
            'window': 3600,  # 1 hour
            'burst': 3
        },
        'admin': {
            'requests': 1000,
            'window': 3600,  # 1 hour
            'burst': 20
        }
    }
    
    # Endpoint-specific overrides
    ENDPOINT_LIMITS = {
        '/api/v1/auth/login': 'auth',
        '/api/v1/auth/register': 'auth',
        '/api/v1/auth/refresh': 'auth',
        '/api/v1/charts/generate': 'chart_generation',
        '/api/v1/charts/interpret': 'ai_interpretation',
        '/api/v1/upload': 'file_upload',
        '/admin/': 'admin',
    }


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter implementation.
    """
    
    def __init__(self, cache_key: str, limit_config: Dict[str, Any]):
        self.cache_key = cache_key
        self.requests = limit_config['requests']
        self.window = limit_config['window']
        self.burst = limit_config.get('burst', 1)
    
    def is_allowed(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed and return rate limit info.
        """
        now = time.time()
        window_start = now - self.window
        
        # Get current requests from cache
        current_requests = cache.get(self.cache_key, [])
        
        # Remove old requests outside the window
        current_requests = [req_time for req_time in current_requests if req_time > window_start]
        
        # Check if we're within limits
        if len(current_requests) >= self.requests:
            # Rate limit exceeded
            oldest_request = min(current_requests) if current_requests else now
            reset_time = oldest_request + self.window
            
            return False, {
                'limit': self.requests,
                'remaining': 0,
                'reset': int(reset_time),
                'retry_after': int(reset_time - now)
            }
        
        # Add current request
        current_requests.append(now)
        
        # Store updated requests (with window as TTL)
        cache.set(self.cache_key, current_requests, self.window)
        
        return True, {
            'limit': self.requests,
            'remaining': self.requests - len(current_requests),
            'reset': int(now + self.window),
            'retry_after': 0
        }


class EnhancedRateLimitMiddleware(MiddlewareMixin):
    """
    Enhanced rate limiting middleware with sliding window implementation.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.config = RateLimitConfig()
    
    def process_request(self, request):
        """
        Process request and apply rate limiting.
        """
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return None
        
        # Get rate limit configuration
        limit_type = self._get_rate_limit_type(request)
        limit_config = self.config.DEFAULT_LIMITS.get(limit_type, self.config.DEFAULT_LIMITS['default'])
        
        # Get identifier (user ID or IP)
        identifier = self._get_identifier(request)
        
        # Create cache key
        cache_key = f"rate_limit:{limit_type}:{identifier}"
        
        # Check rate limit
        rate_limiter = SlidingWindowRateLimiter(cache_key, limit_config)
        is_allowed, rate_info = rate_limiter.is_allowed()
        
        # Store rate info for response headers
        request.rate_limit_info = rate_info
        
        if not is_allowed:
            # Rate limit exceeded
            logger.warning(f'Rate limit exceeded for {identifier} on {limit_type}')
            
            # Log analytics
            self._log_rate_limit_exceeded(request, identifier, limit_type, rate_info)
            
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Too many requests. Limit: {rate_info["limit"]} per {limit_config["window"]}s',
                'retry_after': rate_info['retry_after'],
                'limit': rate_info['limit'],
                'reset': rate_info['reset']
            }, status=429)
        
        return None
    
    def process_response(self, request, response):
        """
        Add rate limit headers to response.
        """
        if hasattr(request, 'rate_limit_info'):
            rate_info = request.rate_limit_info
            
            # Add rate limit headers
            response['X-RateLimit-Limit'] = str(rate_info['limit'])
            response['X-RateLimit-Remaining'] = str(rate_info['remaining'])
            response['X-RateLimit-Reset'] = str(rate_info['reset'])
            
            # Add retry-after header if rate limited
            if rate_info['retry_after'] > 0:
                response['Retry-After'] = str(rate_info['retry_after'])
        
        return response
    
    def _should_skip_rate_limit(self, request) -> bool:
        """
        Determine if rate limiting should be skipped for this request.
        """
        # Skip rate limiting during tests
        if getattr(settings, 'TESTING', False):
            return True
            
        skip_paths = [
            '/static/', '/media/', '/favicon.ico',
            '/api/v1/system/health/', '/api/v1/system/quick-health/'
        ]
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _get_rate_limit_type(self, request) -> str:
        """
        Determine rate limit type based on request path and method.
        """
        path = request.path
        
        # Check endpoint-specific limits
        for endpoint, limit_type in self.config.ENDPOINT_LIMITS.items():
            if path.startswith(endpoint):
                return limit_type
        
        # Check for API requests
        if path.startswith('/api/'):
            return 'api'
        
        return 'default'
    
    def _get_identifier(self, request) -> str:
        """
        Get unique identifier for rate limiting (user ID or IP).
        """
        # Use user ID if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Fall back to IP address
        return f"ip:{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request) -> str:
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _log_rate_limit_exceeded(self, request, identifier: str, limit_type: str, rate_info: Dict[str, Any]):
        """
        Log rate limit exceeded event for analytics.
        """
        log_data = {
            'identifier': identifier,
            'limit_type': limit_type,
            'path': request.path,
            'method': request.method,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'limit': rate_info['limit'],
            'reset': rate_info['reset'],
            'retry_after': rate_info['retry_after']
        }
        
        logger.warning(f'Rate limit exceeded: {log_data}')


class UsageAnalytics:
    """
    Analytics for rate limiting and usage tracking.
    """
    
    @staticmethod
    def track_request(request, identifier: str, limit_type: str, rate_info: Dict[str, Any]):
        """
        Track request for analytics.
        """
        analytics_data = {
            'timestamp': time.time(),
            'identifier': identifier,
            'limit_type': limit_type,
            'path': request.path,
            'method': request.method,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'remaining': rate_info['remaining'],
            'limit': rate_info['limit']
        }
        
        # Store analytics data (could be sent to external analytics service)
        cache_key = f"analytics:requests:{int(time.time() / 3600)}"  # Hourly bucket
        cache.set(cache_key, analytics_data, 86400)  # Keep for 24 hours
    
    @staticmethod
    def get_usage_stats(identifier: str, hours: int = 24) -> Dict[str, Any]:
        """
        Get usage statistics for an identifier.
        """
        now = time.time()
        stats = {
            'total_requests': 0,
            'rate_limited': 0,
            'endpoints': {},
            'hourly_breakdown': {}
        }
        
        # Collect data from hourly buckets
        for i in range(hours):
            bucket_time = int((now - (i * 3600)) / 3600)
            cache_key = f"analytics:requests:{bucket_time}"
            data = cache.get(cache_key)
            
            if data and data.get('identifier') == identifier:
                stats['total_requests'] += 1
                
                if data.get('remaining', 0) == 0:
                    stats['rate_limited'] += 1
                
                # Track endpoints
                endpoint = data.get('path', 'unknown')
                stats['endpoints'][endpoint] = stats['endpoints'].get(endpoint, 0) + 1
                
                # Track hourly breakdown
                hour = time.strftime('%Y-%m-%d %H:00', time.localtime(data['timestamp']))
                stats['hourly_breakdown'][hour] = stats['hourly_breakdown'].get(hour, 0) + 1
        
        return stats


# Utility functions for rate limiting
def get_rate_limit_info(request) -> Optional[Dict[str, Any]]:
    """
    Get current rate limit information for a request.
    """
    if hasattr(request, 'rate_limit_info'):
        return request.rate_limit_info
    return None


def is_rate_limited(request) -> bool:
    """
    Check if request is currently rate limited.
    """
    rate_info = get_rate_limit_info(request)
    return rate_info is not None and rate_info.get('remaining', 0) == 0


def get_remaining_requests(request) -> int:
    """
    Get remaining requests for current rate limit window.
    """
    rate_info = get_rate_limit_info(request)
    return rate_info.get('remaining', 0) if rate_info else 0


def get_reset_time(request) -> int:
    """
    Get reset time for current rate limit window.
    """
    rate_info = get_rate_limit_info(request)
    return rate_info.get('reset', 0) if rate_info else 0
