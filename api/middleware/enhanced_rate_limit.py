"""
Enhanced Rate Limiting Middleware

This module provides sophisticated rate limiting with:
- Tiered rate limits (free/premium users)
- Per-endpoint rate limits
- Usage tracking and analytics
- Cost management for AI operations
- Rate limit headers and responses
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class EnhancedRateLimitMiddleware:
    """
    Enhanced rate limiting middleware with tiered limits and usage tracking
    """
    
    # Rate limit configurations
    RATE_LIMITS = {
        'free_user': {
            'general': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'chart_generation': {'requests': 5, 'window': 3600},  # 5 charts per hour
            'ai_interpretation': {'requests': 10, 'window': 3600},  # 10 interpretations per hour
            'api_calls': {'requests': 200, 'window': 3600},  # 200 API calls per hour
        },
        'premium_user': {
            'general': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
            'chart_generation': {'requests': 50, 'window': 3600},  # 50 charts per hour
            'ai_interpretation': {'requests': 100, 'window': 3600},  # 100 interpretations per hour
            'api_calls': {'requests': 2000, 'window': 3600},  # 2000 API calls per hour
        },
        'admin_user': {
            'general': {'requests': 5000, 'window': 3600},  # 5000 requests per hour
            'chart_generation': {'requests': 200, 'window': 3600},  # 200 charts per hour
            'ai_interpretation': {'requests': 500, 'window': 3600},  # 500 interpretations per hour
            'api_calls': {'requests': 10000, 'window': 3600},  # 10000 API calls per hour
        }
    }
    
    # Endpoint-specific rate limit overrides
    ENDPOINT_LIMITS = {
        '/api/v1/charts/generate/': 'chart_generation',
        '/api/v1/charts/interpret/': 'ai_interpretation',
        '/api/v1/background-charts/generate_chart/': 'chart_generation',
        '/api/v1/background-charts/generate_interpretation/': 'ai_interpretation',
        '/api/v1/auth/login/': {'requests': 10, 'window': 300},  # 10 login attempts per 5 minutes
        '/api/v1/auth/register/': {'requests': 5, 'window': 3600},  # 5 registrations per hour
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = cache
    
    def __call__(self, request):
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return self.get_response(request)
        
        # Get user tier and rate limits
        user_tier = self._get_user_tier(request)
        rate_limits = self.RATE_LIMITS.get(user_tier, self.RATE_LIMITS['free_user'])
        
        # Check rate limits
        rate_limit_result = self._check_rate_limits(request, rate_limits, user_tier)
        
        if not rate_limit_result['allowed']:
            return self._create_rate_limit_response(rate_limit_result)
        
        # Add rate limit headers to response
        response = self.get_response(request)
        self._add_rate_limit_headers(response, rate_limit_result)
        
        # Track usage
        self._track_usage(request, user_tier, rate_limit_result)
        
        return response
    
    def _should_skip_rate_limit(self, request) -> bool:
        """
        Determine if rate limiting should be skipped for this request
        """
        # Skip for admin interface
        if request.path.startswith('/admin/'):
            return True
        
        # Skip for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return True
        
        # Skip for health checks
        if request.path in ['/api/v1/system/health/', '/health/']:
            return True
        
        # Skip for documentation
        if request.path.startswith('/api/docs/') or request.path.startswith('/api/schema/'):
            return True
        
        return False
    
    def _get_user_tier(self, request) -> str:
        """
        Determine user tier based on authentication and subscription status
        """
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return 'free_user'
        
        # Check if user is admin
        if request.user.is_staff or request.user.is_superuser:
            return 'admin_user'
        
        # Check if user has premium subscription
        if hasattr(request.user, 'is_premium') and request.user.is_premium:
            return 'premium_user'
        
        return 'free_user'
    
    def _check_rate_limits(self, request, rate_limits: Dict, user_tier: str) -> Dict[str, Any]:
        """
        Check all applicable rate limits for the request
        """
        current_time = int(time.time())
        client_ip = self._get_client_ip(request)
        user_id = request.user.id if request.user.is_authenticated else None
        
        # Determine which rate limit to check
        limit_type = self._get_limit_type(request)
        limit_config = rate_limits.get(limit_type, rate_limits['general'])
        
        # Handle endpoint-specific overrides
        if request.path in self.ENDPOINT_LIMITS:
            endpoint_limit = self.ENDPOINT_LIMITS[request.path]
            if isinstance(endpoint_limit, str):
                limit_config = rate_limits.get(endpoint_limit, limit_config)
            else:
                limit_config = endpoint_limit
        
        # Create cache key
        cache_key = self._create_cache_key(client_ip, user_id, limit_type, current_time, limit_config['window'])
        
        # Check current usage
        current_usage = self.cache.get(cache_key, 0)
        
        # Check if limit exceeded
        if current_usage >= limit_config['requests']:
            return {
                'allowed': False,
                'limit_type': limit_type,
                'current_usage': current_usage,
                'limit': limit_config['requests'],
                'window': limit_config['window'],
                'reset_time': current_time + limit_config['window'],
                'user_tier': user_tier
            }
        
        # Increment usage
        self.cache.set(cache_key, current_usage + 1, limit_config['window'])
        
        return {
            'allowed': True,
            'limit_type': limit_type,
            'current_usage': current_usage + 1,
            'limit': limit_config['requests'],
            'window': limit_config['window'],
            'reset_time': current_time + limit_config['window'],
            'user_tier': user_tier
        }
    
    def _get_limit_type(self, request) -> str:
        """
        Determine the rate limit type based on the request
        """
        path = request.path
        
        # Check for specific endpoint types
        if 'chart' in path and ('generate' in path or 'interpret' in path):
            return 'chart_generation'
        elif 'ai' in path or 'interpret' in path:
            return 'ai_interpretation'
        elif path.startswith('/api/'):
            return 'api_calls'
        
        return 'general'
    
    def _create_cache_key(self, client_ip: str, user_id: Optional[int], 
                         limit_type: str, current_time: int, window: int) -> str:
        """
        Create a cache key for rate limiting
        """
        # Use user ID if available, otherwise use IP
        identifier = f"user_{user_id}" if user_id else f"ip_{client_ip}"
        
        # Create time window
        window_start = (current_time // window) * window
        
        return f"rate_limit:{limit_type}:{identifier}:{window_start}"
    
    def _get_client_ip(self, request) -> str:
        """
        Get client IP address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _create_rate_limit_response(self, rate_limit_result: Dict[str, Any]) -> JsonResponse:
        """
        Create a rate limit exceeded response
        """
        response_data = {
            'error': 'Rate limit exceeded',
            'message': f'Too many requests for {rate_limit_result["limit_type"]}',
            'limit_type': rate_limit_result['limit_type'],
            'current_usage': rate_limit_result['current_usage'],
            'limit': rate_limit_result['limit'],
            'reset_time': rate_limit_result['reset_time'],
            'user_tier': rate_limit_result['user_tier']
        }
        
        response = JsonResponse(response_data, status=429)
        
        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(rate_limit_result['limit'])
        response['X-RateLimit-Remaining'] = '0'
        response['X-RateLimit-Reset'] = str(rate_limit_result['reset_time'])
        response['X-RateLimit-Type'] = rate_limit_result['limit_type']
        response['X-RateLimit-UserTier'] = rate_limit_result['user_tier']
        
        return response
    
    def _add_rate_limit_headers(self, response, rate_limit_result: Dict[str, Any]):
        """
        Add rate limit headers to response
        """
        remaining = max(0, rate_limit_result['limit'] - rate_limit_result['current_usage'])
        
        response['X-RateLimit-Limit'] = str(rate_limit_result['limit'])
        response['X-RateLimit-Remaining'] = str(remaining)
        response['X-RateLimit-Reset'] = str(rate_limit_result['reset_time'])
        response['X-RateLimit-Type'] = rate_limit_result['limit_type']
        response['X-RateLimit-UserTier'] = rate_limit_result['user_tier']
    
    def _track_usage(self, request, user_tier: str, rate_limit_result: Dict[str, Any]):
        """
        Track API usage for analytics
        """
        try:
            usage_data = {
                'timestamp': timezone.now().isoformat(),
                'user_id': request.user.id if request.user.is_authenticated else None,
                'user_tier': user_tier,
                'endpoint': request.path,
                'method': request.method,
                'limit_type': rate_limit_result['limit_type'],
                'usage_count': 1,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            }
            
            # Store usage data in cache for aggregation
            usage_key = f"usage_stats:{timezone.now().strftime('%Y-%m-%d')}"
            current_stats = self.cache.get(usage_key, {})
            
            # Aggregate usage by user tier and endpoint
            tier_key = f"{user_tier}_{rate_limit_result['limit_type']}"
            if tier_key not in current_stats:
                current_stats[tier_key] = 0
            current_stats[tier_key] += 1
            
            # Store for 24 hours
            self.cache.set(usage_key, current_stats, 86400)
            
        except Exception as e:
            logger.error(f"Error tracking usage: {e}")


class UsageAnalytics:
    """
    Utility class for analyzing API usage patterns
    """
    
    @staticmethod
    def get_daily_usage_stats(date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Get daily usage statistics
        """
        if not date_str:
            date_str = timezone.now().strftime('%Y-%m-%d')
        
        cache_key = f"usage_stats:{date_str}"
        stats = cache.get(cache_key, {})
        
        # Parse and organize stats
        organized_stats = {
            'date': date_str,
            'total_requests': 0,
            'by_user_tier': {},
            'by_endpoint': {},
            'by_limit_type': {}
        }
        
        for key, count in stats.items():
            if '_' in key:
                tier, limit_type = key.split('_', 1)
                
                # Add to total
                organized_stats['total_requests'] += count
                
                # Add to tier breakdown
                if tier not in organized_stats['by_user_tier']:
                    organized_stats['by_user_tier'][tier] = 0
                organized_stats['by_user_tier'][tier] += count
                
                # Add to limit type breakdown
                if limit_type not in organized_stats['by_limit_type']:
                    organized_stats['by_limit_type'][limit_type] = 0
                organized_stats['by_limit_type'][limit_type] += count
        
        return organized_stats
    
    @staticmethod
    def get_user_usage_summary(user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get usage summary for a specific user
        """
        # This would typically query a database table for user usage
        # For now, we'll return a placeholder
        return {
            'user_id': user_id,
            'period_days': days,
            'total_requests': 0,
            'chart_generations': 0,
            'ai_interpretations': 0,
            'api_calls': 0,
            'estimated_cost': 0.0
        }
    
    @staticmethod
    def estimate_ai_cost(interpretations_count: int, model: str = 'gpt-4') -> float:
        """
        Estimate cost for AI interpretations
        """
        # Rough cost estimates (these would be updated based on actual usage)
        cost_per_interpretation = {
            'gpt-4': 0.05,  # $0.05 per interpretation
            'gpt-3.5-turbo': 0.01,  # $0.01 per interpretation
            'claude-3': 0.03,  # $0.03 per interpretation
        }
        
        return interpretations_count * cost_per_interpretation.get(model, 0.05)


# Global rate limit middleware instance
enhanced_rate_limit_middleware = EnhancedRateLimitMiddleware 