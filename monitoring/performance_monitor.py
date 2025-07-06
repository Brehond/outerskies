"""
Performance Monitoring System for Outer Skies

This module provides comprehensive performance monitoring:
- Request/response time tracking
- Database query performance
- Cache hit/miss rates
- Memory and CPU usage
- API endpoint performance
- Background task performance
"""

import time
import logging
import psutil
import threading
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from collections import defaultdict, deque
import json
import statistics

logger = logging.getLogger(__name__)


class PerformanceMetric:
    """Represents a single performance metric"""
    
    def __init__(self, name: str, value: float, unit: str = "ms", 
                 timestamp: datetime = None, metadata: Dict[str, Any] = None):
        self.name = name
        self.value = value
        self.unit = unit
        self.timestamp = timestamp or timezone.now()
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.db_queries: deque = deque(maxlen=1000)
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
        self.lock = threading.Lock()
        
        # Initialize system monitoring
        self._start_system_monitoring()
    
    def _start_system_monitoring(self):
        """Start background system monitoring"""
        def monitor_system():
            while True:
                try:
                    self._record_system_metrics()
                    time.sleep(60)  # Record every minute
                except Exception as e:
                    logger.error(f"System monitoring error: {e}")
                    time.sleep(60)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_system, daemon=True)
        monitor_thread.start()
    
    def _record_system_metrics(self):
        """Record system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.record_metric('system.cpu_usage', cpu_percent, 'percent')
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.record_metric('system.memory_usage', memory.percent, 'percent')
            self.record_metric('system.memory_available', memory.available / (1024**3), 'gb')
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.record_metric('system.disk_usage', disk.percent, 'percent')
            self.record_metric('system.disk_free', disk.free / (1024**3), 'gb')
            
            # Network I/O
            net_io = psutil.net_io_counters()
            self.record_metric('system.network_bytes_sent', net_io.bytes_sent, 'bytes')
            self.record_metric('system.network_bytes_recv', net_io.bytes_recv, 'bytes')
            
        except Exception as e:
            logger.error(f"Error recording system metrics: {e}")
    
    def record_metric(self, name: str, value: float, unit: str = "ms", 
                     metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        with self.lock:
            metric = PerformanceMetric(name, value, unit, metadata=metadata)
            self.metrics[name].append(metric)
    
    def record_request_time(self, endpoint: str, method: str, duration: float, 
                          status_code: int = None, user_id: int = None):
        """Record request/response time"""
        with self.lock:
            key = f"{method}:{endpoint}"
            self.request_times[key].append({
                'duration': duration,
                'timestamp': timezone.now(),
                'status_code': status_code,
                'user_id': user_id
            })
    
    def record_database_query(self, sql: str, duration: float, table: str = None):
        """Record database query performance"""
        with self.lock:
            self.db_queries.append({
                'sql': sql[:200] + '...' if len(sql) > 200 else sql,  # Truncate long queries
                'duration': duration,
                'timestamp': timezone.now(),
                'table': table
            })
    
    def record_cache_operation(self, operation: str, success: bool):
        """Record cache operation"""
        with self.lock:
            if operation == 'hit':
                self.cache_stats['hits'] += 1
            elif operation == 'miss':
                self.cache_stats['misses'] += 1
            elif operation == 'set':
                self.cache_stats['sets'] += 1
            elif operation == 'delete':
                self.cache_stats['deletes'] += 1
    
    def get_metric_stats(self, metric_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for a specific metric"""
        with self.lock:
            cutoff_time = timezone.now() - timedelta(minutes=minutes)
            recent_metrics = [
                m for m in self.metrics[metric_name]
                if m.timestamp >= cutoff_time
            ]
            
            if not recent_metrics:
                return {
                    'count': 0,
                    'min': 0,
                    'max': 0,
                    'avg': 0,
                    'median': 0
                }
            
            values = [m.value for m in recent_metrics]
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': statistics.mean(values),
                'median': statistics.median(values),
                'unit': recent_metrics[0].unit if recent_metrics else 'ms'
            }
    
    def get_request_performance(self, minutes: int = 60) -> Dict[str, Any]:
        """Get request performance statistics"""
        with self.lock:
            cutoff_time = timezone.now() - timedelta(minutes=minutes)
            endpoint_stats = {}
            
            for endpoint, times in self.request_times.items():
                recent_times = [
                    t for t in times if t['timestamp'] >= cutoff_time
                ]
                
                if recent_times:
                    durations = [t['duration'] for t in recent_times]
                    status_codes = [t['status_code'] for t in recent_times if t['status_code']]
                    
                    endpoint_stats[endpoint] = {
                        'count': len(recent_times),
                        'avg_duration': statistics.mean(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations),
                        'median_duration': statistics.median(durations),
                        'success_rate': sum(1 for sc in status_codes if 200 <= sc < 400) / len(status_codes) if status_codes else 0
                    }
            
            return endpoint_stats
    
    def get_database_performance(self, minutes: int = 60) -> Dict[str, Any]:
        """Get database performance statistics"""
        with self.lock:
            cutoff_time = timezone.now() - timedelta(minutes=minutes)
            recent_queries = [
                q for q in self.db_queries if q['timestamp'] >= cutoff_time
            ]
            
            if not recent_queries:
                return {
                    'total_queries': 0,
                    'avg_duration': 0,
                    'slow_queries': 0,
                    'table_stats': {}
                }
            
            durations = [q['duration'] for q in recent_queries]
            slow_queries = [q for q in recent_queries if q['duration'] > 1.0]  # > 1 second
            
            # Group by table
            table_stats = defaultdict(list)
            for query in recent_queries:
                if query['table']:
                    table_stats[query['table']].append(query['duration'])
            
            table_performance = {}
            for table, table_durations in table_stats.items():
                table_performance[table] = {
                    'count': len(table_durations),
                    'avg_duration': statistics.mean(table_durations),
                    'max_duration': max(table_durations)
                }
            
            return {
                'total_queries': len(recent_queries),
                'avg_duration': statistics.mean(durations),
                'max_duration': max(durations),
                'slow_queries': len(slow_queries),
                'slow_query_percentage': len(slow_queries) / len(recent_queries) * 100,
                'table_stats': table_performance
            }
    
    def get_cache_performance(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self.lock:
            total_operations = (
                self.cache_stats['hits'] + 
                self.cache_stats['misses'] + 
                self.cache_stats['sets'] + 
                self.cache_stats['deletes']
            )
            
            if total_operations == 0:
                hit_rate = 0
            else:
                hit_rate = self.cache_stats['hits'] / (self.cache_stats['hits'] + self.cache_stats['misses']) * 100
            
            return {
                'hit_rate_percent': round(hit_rate, 2),
                'total_operations': total_operations,
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'sets': self.cache_stats['sets'],
                'deletes': self.cache_stats['deletes']
            }
    
    def get_system_performance(self, minutes: int = 60) -> Dict[str, Any]:
        """Get overall system performance summary"""
        return {
            'cpu_usage': self.get_metric_stats('system.cpu_usage', minutes),
            'memory_usage': self.get_metric_stats('system.memory_usage', minutes),
            'disk_usage': self.get_metric_stats('system.disk_usage', minutes),
            'network_io': {
                'bytes_sent': self.get_metric_stats('system.network_bytes_sent', minutes),
                'bytes_recv': self.get_metric_stats('system.network_bytes_recv', minutes)
            }
        }
    
    def get_performance_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'timestamp': timezone.now().isoformat(),
            'period_minutes': minutes,
            'system': self.get_system_performance(minutes),
            'requests': self.get_request_performance(minutes),
            'database': self.get_database_performance(minutes),
            'cache': self.get_cache_performance(),
            'alerts': self._generate_alerts(minutes)
        }
    
    def _generate_alerts(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Generate performance alerts"""
        alerts = []
        
        # Check system metrics
        cpu_stats = self.get_metric_stats('system.cpu_usage', minutes)
        if cpu_stats['avg'] > 80:
            alerts.append({
                'level': 'warning',
                'message': f"High CPU usage: {cpu_stats['avg']:.1f}%",
                'metric': 'cpu_usage'
            })
        
        memory_stats = self.get_metric_stats('system.memory_usage', minutes)
        if memory_stats['avg'] > 85:
            alerts.append({
                'level': 'warning',
                'message': f"High memory usage: {memory_stats['avg']:.1f}%",
                'metric': 'memory_usage'
            })
        
        # Check database performance
        db_stats = self.get_database_performance(minutes)
        if db_stats['avg_duration'] > 0.5:  # > 500ms
            alerts.append({
                'level': 'warning',
                'message': f"Slow database queries: {db_stats['avg_duration']:.3f}s average",
                'metric': 'database_performance'
            })
        
        # Check cache performance
        cache_stats = self.get_cache_performance()
        if cache_stats['hit_rate_percent'] < 50:
            alerts.append({
                'level': 'info',
                'message': f"Low cache hit rate: {cache_stats['hit_rate_percent']:.1f}%",
                'metric': 'cache_performance'
            })
        
        return alerts


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Decorator for monitoring function performance
def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # Convert to ms
                performance_monitor.record_metric(metric_name, duration)
                return result
            except Exception as e:
                duration = (time.time() - start_time) * 1000
                performance_monitor.record_metric(f"{metric_name}_error", duration, 
                                                metadata={'error': str(e)})
                raise
        return wrapper
    return decorator


# Middleware for request monitoring
class PerformanceMonitoringMiddleware:
    """Django middleware for monitoring request performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Record performance
        duration = (time.time() - start_time) * 1000  # Convert to ms
        endpoint = request.path
        method = request.method
        status_code = response.status_code
        user_id = request.user.id if request.user.is_authenticated else None
        
        performance_monitor.record_request_time(endpoint, method, duration, 
                                              status_code, user_id)
        
        return response


# Database query monitoring
class DatabaseQueryMonitor:
    """Monitor database query performance"""
    
    def __init__(self):
        self.original_execute = None
        self.installed = False
    
    def install(self):
        """Install database query monitoring"""
        if self.installed:
            return
            
        try:
            # Get the original execute method
            cursor = connection.cursor()
            self.original_execute = cursor.execute
            
            def monitored_execute(cursor, sql, params=None):
                start_time = time.time()
                try:
                    result = self.original_execute(cursor, sql, params)
                    duration = (time.time() - start_time) * 1000
                    
                    # Extract table name from SQL (simplified)
                    table = None
                    sql_upper = sql.upper()
                    if 'FROM ' in sql_upper:
                        table = sql_upper.split('FROM ')[1].split()[0]
                    elif 'UPDATE ' in sql_upper:
                        table = sql_upper.split('UPDATE ')[1].split()[0]
                    elif 'INSERT INTO ' in sql_upper:
                        table = sql_upper.split('INSERT INTO ')[1].split()[0]
                    
                    performance_monitor.record_database_query(sql, duration, table)
                    return result
                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    performance_monitor.record_database_query(sql, duration, 
                                                            metadata={'error': str(e)})
                    raise
            
            # Replace the execute method
            cursor.execute = monitored_execute
            self.installed = True
            
        except Exception as e:
            logger.warning(f"Could not install database monitoring: {e}")
            self.installed = False


# Initialize database monitoring lazily
db_monitor = None

def get_db_monitor():
    """Get or create database monitor instance"""
    global db_monitor
    if db_monitor is None:
        try:
            db_monitor = DatabaseQueryMonitor()
            # Don't install immediately - let it be installed when needed
        except Exception as e:
            logger.warning(f"Could not create database monitor: {e}")
            db_monitor = None
    return db_monitor


def get_performance_summary(minutes: int = 60) -> Dict[str, Any]:
    """Get performance summary for the specified time period"""
    return performance_monitor.get_performance_summary(minutes)


def record_metric(name: str, value: float, unit: str = "ms", metadata: Dict[str, Any] = None):
    """Record a performance metric"""
    performance_monitor.record_metric(name, value, unit, metadata)


def ensure_db_monitoring():
    """Ensure database monitoring is installed"""
    monitor = get_db_monitor()
    if monitor and not monitor.installed:
        monitor.install()


def monitor_response_time() -> Dict[str, Any]:
    """Monitor response time metrics"""
    try:
        return performance_monitor.get_request_performance(minutes=5)
    except Exception as e:
        return {'error': str(e)}


def monitor_database_performance() -> Dict[str, Any]:
    """Monitor database performance metrics"""
    try:
        return performance_monitor.get_database_performance(minutes=5)
    except Exception as e:
        return {'error': str(e)}


def monitor_cache_performance() -> Dict[str, Any]:
    """Monitor cache performance metrics"""
    try:
        return performance_monitor.get_cache_performance()
    except Exception as e:
        return {'error': str(e)} 