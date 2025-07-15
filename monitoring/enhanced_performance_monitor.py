"""
Enhanced Performance Monitoring Service

This module provides comprehensive performance monitoring including:
- Real-time performance metrics
- Request/response profiling
- Memory and CPU monitoring
- Performance alerts and thresholds
- Historical performance tracking
- Performance optimization recommendations
"""

import time
import psutil
import threading
import logging
from typing import Dict, Any, List, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timedelta
from functools import wraps
import json
import os
from dataclasses import dataclass, asdict
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    timestamp: datetime
    operation: str
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SystemMetrics:
    """System-level performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    network_io: Dict[str, float]
    active_threads: int
    open_files: int


class PerformanceProfiler:
    """Profiles function performance with detailed metrics"""
    
    def __init__(self, max_samples: int = 1000):
        self.metrics = deque(maxlen=max_samples)
        self.operation_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0,
            'last_execution': None
        })
        self.lock = threading.Lock()
    
    def profile(self, operation_name: str = None):
        """Decorator to profile function performance"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                op_name = operation_name or func.__name__
                start_time = time.time()
                success = True
                error_msg = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_msg = str(e)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self._record_metric(op_name, duration_ms, success, error_msg)
            
            return wrapper
        return decorator
    
    def _record_metric(self, operation: str, duration_ms: float, success: bool, error_msg: Optional[str] = None):
        """Record a performance metric"""
        with self.lock:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                error_message=error_msg
            )
            
            self.metrics.append(metric)
            
            # Update operation statistics
            stats = self.operation_stats[operation]
            stats['count'] += 1
            stats['total_time'] += duration_ms
            stats['min_time'] = min(stats['min_time'], duration_ms)
            stats['max_time'] = max(stats['max_time'], duration_ms)
            stats['last_execution'] = datetime.now()
            
            if not success:
                stats['errors'] += 1
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        with self.lock:
            stats = self.operation_stats.get(operation, {})
            if stats['count'] > 0:
                return {
                    'operation': operation,
                    'count': stats['count'],
                    'average_time_ms': round(stats['total_time'] / stats['count'], 2),
                    'min_time_ms': round(stats['min_time'], 2),
                    'max_time_ms': round(stats['max_time'], 2),
                    'error_rate_percent': round(stats['errors'] / stats['count'] * 100, 2),
                    'last_execution': stats['last_execution'].isoformat() if stats['last_execution'] else None
                }
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all operations"""
        with self.lock:
            return {
                operation: self.get_operation_stats(operation)
                for operation in self.operation_stats.keys()
            }


class SystemMonitor:
    """Monitors system performance metrics"""
    
    def __init__(self, sample_interval: int = 60):
        self.sample_interval = sample_interval
        self.metrics = deque(maxlen=1440)  # Store 24 hours of data (1 sample per minute)
        self.monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()
    
    def start_monitoring(self):
        """Start system monitoring in background thread"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("System monitoring started")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("System monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                metrics = self._collect_system_metrics()
                with self.lock:
                    self.metrics.append(metrics)
                
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                time.sleep(self.sample_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_mb=memory.used / (1024 * 1024),
            memory_available_mb=memory.available / (1024 * 1024),
            disk_usage_percent=disk.percent,
            network_io={
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            },
            active_threads=threading.active_count(),
            open_files=len(psutil.Process().open_files())
        )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        metrics = self._collect_system_metrics()
        return asdict(metrics)
    
    def get_historical_metrics(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get historical system metrics"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            recent_metrics = [
                asdict(metric) for metric in self.metrics
                if metric.timestamp >= cutoff_time
            ]
        
        return recent_metrics


class PerformanceAlert:
    """Performance alert configuration"""
    
    def __init__(self, name: str, condition: Callable, threshold: float, 
                 severity: str = 'warning', cooldown_minutes: int = 5):
        self.name = name
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered = None
    
    def should_trigger(self, current_value: float) -> bool:
        """Check if alert should be triggered"""
        if self.condition(current_value, self.threshold):
            # Check cooldown
            if (self.last_triggered is None or 
                datetime.now() - self.last_triggered > timedelta(minutes=self.cooldown_minutes)):
                self.last_triggered = datetime.now()
                return True
        return False


class EnhancedPerformanceMonitor:
    """
    Enhanced performance monitoring service
    """
    
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.system_monitor = SystemMonitor()
        self.alerts = []
        self.alert_handlers = []
        self._setup_default_alerts()
        self._setup_default_handlers()
    
    def _setup_default_alerts(self):
        """Setup default performance alerts"""
        self.alerts = [
            PerformanceAlert(
                name="High CPU Usage",
                condition=lambda current, threshold: current > threshold,
                threshold=80.0,
                severity="warning"
            ),
            PerformanceAlert(
                name="High Memory Usage",
                condition=lambda current, threshold: current > threshold,
                threshold=85.0,
                severity="warning"
            ),
            PerformanceAlert(
                name="Slow Operation",
                condition=lambda current, threshold: current > threshold,
                threshold=1000.0,  # 1 second
                severity="warning"
            ),
            PerformanceAlert(
                name="High Error Rate",
                condition=lambda current, threshold: current > threshold,
                threshold=5.0,  # 5% error rate
                severity="critical"
            )
        ]
    
    def _setup_default_handlers(self):
        """Setup default alert handlers"""
        def log_alert(alert: PerformanceAlert, current_value: float, context: Dict[str, Any]):
            logger.warning(f"Performance Alert: {alert.name} - Current: {current_value}, Threshold: {alert.threshold}")
        
        def cache_alert(alert: PerformanceAlert, current_value: float, context: Dict[str, Any]):
            alert_data = {
                'name': alert.name,
                'severity': alert.severity,
                'current_value': current_value,
                'threshold': alert.threshold,
                'timestamp': datetime.now().isoformat(),
                'context': context
            }
            cache.set(f"performance_alert_{alert.name}", alert_data, timeout=3600)
        
        self.alert_handlers = [log_alert, cache_alert]
    
    def add_alert(self, alert: PerformanceAlert):
        """Add a custom performance alert"""
        self.alerts.append(alert)
    
    def add_alert_handler(self, handler: Callable):
        """Add a custom alert handler"""
        self.alert_handlers.append(handler)
    
    def check_alerts(self, context: Dict[str, Any] = None):
        """Check all performance alerts"""
        context = context or {}
        
        # Check system metrics
        system_metrics = self.system_monitor.get_current_metrics()
        
        for alert in self.alerts:
            if alert.name == "High CPU Usage":
                if alert.should_trigger(system_metrics['cpu_percent']):
                    self._trigger_alert(alert, system_metrics['cpu_percent'], context)
            
            elif alert.name == "High Memory Usage":
                if alert.should_trigger(system_metrics['memory_percent']):
                    self._trigger_alert(alert, system_metrics['memory_percent'], context)
        
        # Check operation metrics
        operation_stats = self.profiler.get_all_stats()
        for operation, stats in operation_stats.items():
            if stats.get('average_time_ms', 0) > 1000:  # Slow operation
                slow_alert = next((a for a in self.alerts if a.name == "Slow Operation"), None)
                if slow_alert and slow_alert.should_trigger(stats['average_time_ms']):
                    self._trigger_alert(slow_alert, stats['average_time_ms'], 
                                      {**context, 'operation': operation})
            
            if stats.get('error_rate_percent', 0) > 5:  # High error rate
                error_alert = next((a for a in self.alerts if a.name == "High Error Rate"), None)
                if error_alert and error_alert.should_trigger(stats['error_rate_percent']):
                    self._trigger_alert(error_alert, stats['error_rate_percent'], 
                                      {**context, 'operation': operation})
    
    def _trigger_alert(self, alert: PerformanceAlert, current_value: float, context: Dict[str, Any]):
        """Trigger an alert"""
        for handler in self.alert_handlers:
            try:
                handler(alert, current_value, context)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.system_monitor.start_monitoring()
        logger.info("Enhanced performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.system_monitor.stop_monitoring()
        logger.info("Enhanced performance monitoring stopped")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        system_metrics = self.system_monitor.get_current_metrics()
        operation_stats = self.profiler.get_all_stats()
        
        # Calculate overall performance score
        performance_score = self._calculate_performance_score(system_metrics, operation_stats)
        
        # Get recommendations
        recommendations = self._generate_recommendations(system_metrics, operation_stats)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'performance_score': performance_score,
            'system_metrics': system_metrics,
            'operation_stats': operation_stats,
            'recommendations': recommendations,
            'alerts': self._get_active_alerts()
        }
    
    def _calculate_performance_score(self, system_metrics: Dict[str, Any], 
                                   operation_stats: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)"""
        score = 100.0
        
        # System metrics impact
        if system_metrics['cpu_percent'] > 80:
            score -= 20
        elif system_metrics['cpu_percent'] > 60:
            score -= 10
        
        if system_metrics['memory_percent'] > 85:
            score -= 20
        elif system_metrics['memory_percent'] > 70:
            score -= 10
        
        # Operation performance impact
        for operation, stats in operation_stats.items():
            if stats.get('average_time_ms', 0) > 1000:
                score -= 15
            elif stats.get('average_time_ms', 0) > 500:
                score -= 5
            
            if stats.get('error_rate_percent', 0) > 5:
                score -= 20
            elif stats.get('error_rate_percent', 0) > 1:
                score -= 5
        
        return max(0.0, min(100.0, score))
    
    def _generate_recommendations(self, system_metrics: Dict[str, Any], 
                                operation_stats: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # System recommendations
        if system_metrics['cpu_percent'] > 80:
            recommendations.append("CPU usage is very high - consider scaling up or optimizing CPU-intensive operations")
        elif system_metrics['cpu_percent'] > 60:
            recommendations.append("CPU usage is elevated - monitor for performance degradation")
        
        if system_metrics['memory_percent'] > 85:
            recommendations.append("Memory usage is very high - consider increasing memory or optimizing memory usage")
        elif system_metrics['memory_percent'] > 70:
            recommendations.append("Memory usage is elevated - monitor for memory leaks")
        
        # Operation recommendations
        slow_operations = [
            (op, stats) for op, stats in operation_stats.items()
            if stats.get('average_time_ms', 0) > 1000
        ]
        
        if slow_operations:
            slow_op_names = [op for op, _ in slow_operations]
            recommendations.append(f"Slow operations detected: {', '.join(slow_op_names)} - consider optimization")
        
        high_error_ops = [
            (op, stats) for op, stats in operation_stats.items()
            if stats.get('error_rate_percent', 0) > 5
        ]
        
        if high_error_ops:
            error_op_names = [op for op, _ in high_error_ops]
            recommendations.append(f"High error rates detected: {', '.join(error_op_names)} - investigate error causes")
        
        if not recommendations:
            recommendations.append("Performance is optimal - continue monitoring")
        
        return recommendations
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        active_alerts = []
        
        for alert in self.alerts:
            if alert.last_triggered:
                # Check if alert is still active (within last 10 minutes)
                if datetime.now() - alert.last_triggered < timedelta(minutes=10):
                    active_alerts.append({
                        'name': alert.name,
                        'severity': alert.severity,
                        'threshold': alert.threshold,
                        'triggered_at': alert.last_triggered.isoformat()
                    })
        
        return active_alerts


# Global instance
performance_monitor = EnhancedPerformanceMonitor()


def monitor_performance(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.profiler._record_metric(op_name, duration_ms, True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                performance_monitor.profiler._record_metric(op_name, duration_ms, False, str(e))
                raise
        
        return wrapper
    return decorator 