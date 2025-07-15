"""
API Performance Monitoring Service

Provides comprehensive monitoring for API performance, response times, error rates,
and resource usage. Designed for commercial scale monitoring and alerting.
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
from collections import defaultdict, deque
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.core.cache import cache

logger = logging.getLogger('api.performance')


class PerformanceMetrics:
    """
    Track performance metrics for API endpoints and operations.
    """
    
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.response_times = deque(maxlen=max_samples)
        self.error_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        self.active_requests = 0
        self.total_requests = 0
        self.total_errors = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def record_request(self, endpoint: str, method: str, response_time: float, status_code: int):
        """Record a single request."""
        with self._lock:
            self.response_times.append(response_time)
            self.request_counts[f"{method} {endpoint}"] += 1
            self.total_requests += 1
            
            if status_code >= 400:
                self.error_counts[f"{method} {endpoint}"] += 1
                self.total_errors += 1
    
    def record_active_request(self, active: bool):
        """Record active request count."""
        with self._lock:
            if active:
                self.active_requests += 1
            else:
                self.active_requests = max(0, self.active_requests - 1)
    
    @property
    def avg_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def p95_response_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[index]
    
    @property
    def p99_response_time(self) -> float:
        """Calculate 99th percentile response time."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * 0.99)
        return sorted_times[index]
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_errors / self.total_requests) * 100
    
    @property
    def requests_per_minute(self) -> float:
        """Calculate requests per minute."""
        uptime_minutes = (time.time() - self.start_time) / 60
        if uptime_minutes == 0:
            return 0.0
        return self.total_requests / uptime_minutes
    
    def get_endpoint_stats(self, endpoint: str, method: str = None) -> Dict[str, Any]:
        """Get statistics for a specific endpoint."""
        key = f"{method} {endpoint}" if method else endpoint
        
        with self._lock:
            requests = self.request_counts.get(key, 0)
            errors = self.error_counts.get(key, 0)
            
            return {
                'endpoint': endpoint,
                'method': method,
                'total_requests': requests,
                'total_errors': errors,
                'error_rate': (errors / requests * 100) if requests > 0 else 0.0,
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        return {
            'total_requests': self.total_requests,
            'total_errors': self.total_errors,
            'error_rate': self.error_rate,
            'avg_response_time': self.avg_response_time,
            'p95_response_time': self.p95_response_time,
            'p99_response_time': self.p99_response_time,
            'requests_per_minute': self.requests_per_minute,
            'active_requests': self.active_requests,
            'uptime_minutes': (time.time() - self.start_time) / 60,
        }


class PerformanceMonitor:
    """
    Main performance monitoring service.
    """
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD', 1.0)  # seconds
        self.error_rate_threshold = getattr(settings, 'ERROR_RATE_THRESHOLD', 5.0)  # percentage
        self._monitoring_enabled = getattr(settings, 'PERFORMANCE_MONITORING_ENABLED', True)
    
    def monitor_request(self, endpoint: str = None, method: str = None):
        """
        Decorator to monitor API request performance.
        """
        def decorator(func):
            @wraps(func)
            def wrapper(request: HttpRequest, *args, **kwargs):
                if not self._monitoring_enabled:
                    return func(request, *args, **kwargs)
                
                # Determine endpoint if not provided
                if endpoint is None:
                    endpoint_name = request.path
                else:
                    endpoint_name = endpoint
                
                # Determine method if not provided
                if method is None:
                    method_name = request.method
                else:
                    method_name = method
                
                # Record start time
                start_time = time.time()
                self.metrics.record_active_request(True)
                
                try:
                    # Execute the view
                    response = func(request, *args, **kwargs)
                    
                    # Record metrics
                    response_time = time.time() - start_time
                    self.metrics.record_request(
                        endpoint_name, 
                        method_name, 
                        response_time, 
                        response.status_code
                    )
                    
                    # Log slow requests
                    if response_time > self.slow_query_threshold:
                        logger.warning(
                            f"Slow request detected: {method_name} {endpoint_name} "
                            f"took {response_time:.3f}s (threshold: {self.slow_query_threshold}s)"
                        )
                    
                    return response
                
                except Exception as e:
                    # Record error
                    response_time = time.time() - start_time
                    self.metrics.record_request(
                        endpoint_name, 
                        method_name, 
                        response_time, 
                        500
                    )
                    
                    logger.error(
                        f"Request error: {method_name} {endpoint_name} "
                        f"failed after {response_time:.3f}s: {str(e)}"
                    )
                    raise
                
                finally:
                    self.metrics.record_active_request(False)
            
            return wrapper
        return decorator
    
    def monitor_database_query(self, threshold: float = None):
        """
        Decorator to monitor database query performance.
        """
        if threshold is None:
            threshold = self.slow_query_threshold
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self._monitoring_enabled:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    
                    query_time = time.time() - start_time
                    
                    if query_time > threshold:
                        logger.warning(
                            f"Slow database query detected: {func.__name__} "
                            f"took {query_time:.3f}s (threshold: {threshold}s)"
                        )
                    
                    return result
                
                except Exception as e:
                    query_time = time.time() - start_time
                    logger.error(
                        f"Database query error: {func.__name__} "
                        f"failed after {query_time:.3f}s: {str(e)}"
                    )
                    raise
            
            return wrapper
        return decorator
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.metrics.get_summary()
    
    def get_endpoint_metrics(self, endpoint: str, method: str = None) -> Dict[str, Any]:
        """Get metrics for a specific endpoint."""
        return self.metrics.get_endpoint_stats(endpoint, method)
    
    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for performance alerts."""
        alerts = []
        summary = self.metrics.get_summary()
        
        # Check error rate
        if summary['error_rate'] > self.error_rate_threshold:
            alerts.append({
                'type': 'high_error_rate',
                'message': f"Error rate is {summary['error_rate']:.2f}% (threshold: {self.error_rate_threshold}%)",
                'severity': 'warning',
                'value': summary['error_rate'],
                'threshold': self.error_rate_threshold
            })
        
        # Check response time
        if summary['p95_response_time'] > self.slow_query_threshold:
            alerts.append({
                'type': 'slow_response_time',
                'message': f"P95 response time is {summary['p95_response_time']:.3f}s (threshold: {self.slow_query_threshold}s)",
                'severity': 'warning',
                'value': summary['p95_response_time'],
                'threshold': self.slow_query_threshold
            })
        
        return alerts
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.metrics = PerformanceMetrics()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Convenience decorators
def monitor_api_request(endpoint: str = None, method: str = None):
    """Decorator to monitor API request performance."""
    return performance_monitor.monitor_request(endpoint, method)


def monitor_database_query(threshold: float = None):
    """Decorator to monitor database query performance."""
    return performance_monitor.monitor_database_query(threshold)


# Middleware for automatic request monitoring
class PerformanceMonitoringMiddleware:
    """
    Django middleware for automatic performance monitoring.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.monitor = performance_monitor
    
    def __call__(self, request):
        if not self.monitor._monitoring_enabled:
            return self.get_response(request)
        
        # Record start time
        start_time = time.time()
        self.monitor.metrics.record_active_request(True)
        
        try:
            # Process request
            response = self.get_response(request)
            
            # Record metrics
            response_time = time.time() - start_time
            self.monitor.metrics.record_request(
                request.path,
                request.method,
                response_time,
                response.status_code
            )
            
            # Add performance headers
            response['X-Response-Time'] = f"{response_time:.3f}s"
            response['X-Request-ID'] = getattr(request, 'request_id', 'unknown')
            
            return response
        
        except Exception as e:
            # Record error
            response_time = time.time() - start_time
            self.monitor.metrics.record_request(
                request.path,
                request.method,
                response_time,
                500
            )
            raise
        
        finally:
            self.monitor.metrics.record_active_request(False) 