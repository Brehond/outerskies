"""
Performance Monitor Middleware for Outer Skies
Monitors request performance and provides metrics for optimization.
"""

import time
import logging
from typing import Dict, Any, Optional
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class PerformanceMonitorMiddleware(MiddlewareMixin):
    """
    Middleware to monitor request performance and collect metrics.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 1.0)
        self.metrics_enabled = getattr(settings, 'PERFORMANCE_MONITORING_ENABLED', True)
        
    def process_request(self, request: HttpRequest) -> None:
        """Record request start time."""
        if not self.metrics_enabled:
            return None
            
        request.start_time = time.time()
        return None
        
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Record response time and collect metrics."""
        if not self.metrics_enabled or not hasattr(request, 'start_time'):
            return response
            
        # Calculate response time
        response_time = time.time() - request.start_time
        
        # Log slow requests
        if response_time > self.slow_query_threshold:
            logger.warning(
                f'Slow request detected: {request.path} took {response_time:.3f}s '
                f'(threshold: {self.slow_query_threshold}s)'
            )
            
        # Store metrics in cache
        self._store_metrics(request, response, response_time)
        
        # Add performance headers
        response['X-Response-Time'] = f'{response_time:.3f}s'
        
        return response
        
    def _store_metrics(self, request: HttpRequest, response: HttpResponse, response_time: float) -> None:
        """Store performance metrics in cache."""
        try:
            # Get current metrics
            metrics_key = 'performance_metrics'
            metrics = cache.get(metrics_key, {
                'total_requests': 0,
                'total_response_time': 0.0,
                'slow_requests': 0,
                'error_requests': 0,
                'endpoints': {}
            })
            
            # Update metrics
            metrics['total_requests'] += 1
            metrics['total_response_time'] += response_time
            
            if response_time > self.slow_query_threshold:
                metrics['slow_requests'] += 1
                
            if response.status_code >= 400:
                metrics['error_requests'] += 1
                
            # Update endpoint-specific metrics
            endpoint = request.path
            if endpoint not in metrics['endpoints']:
                metrics['endpoints'][endpoint] = {
                    'count': 0,
                    'total_time': 0.0,
                    'avg_time': 0.0
                }
                
            endpoint_metrics = metrics['endpoints'][endpoint]
            endpoint_metrics['count'] += 1
            endpoint_metrics['total_time'] += response_time
            endpoint_metrics['avg_time'] = endpoint_metrics['total_time'] / endpoint_metrics['count']
            
            # Store updated metrics (keep for 1 hour)
            cache.set(metrics_key, metrics, timeout=3600)
            
        except Exception as e:
            logger.error(f'Error storing performance metrics: {e}')
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        try:
            metrics = cache.get('performance_metrics', {})
            if metrics:
                # Calculate averages
                total_requests = metrics.get('total_requests', 0)
                if total_requests > 0:
                    metrics['avg_response_time'] = metrics['total_response_time'] / total_requests
                    metrics['error_rate'] = metrics['error_requests'] / total_requests
                    metrics['slow_request_rate'] = metrics['slow_requests'] / total_requests
                else:
                    metrics['avg_response_time'] = 0.0
                    metrics['error_rate'] = 0.0
                    metrics['slow_request_rate'] = 0.0
                    
            return metrics
        except Exception as e:
            logger.error(f'Error retrieving performance metrics: {e}')
            return {} 