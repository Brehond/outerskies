"""
Production Monitoring System for Outer Skies
Comprehensive monitoring, alerting, and performance tracking for commercial deployment
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
import psutil
import redis
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Avg, Max, Min
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
import requests
from prometheus_client import Counter, Histogram, Gauge, Summary, generate_latest
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('outer_skies_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('outer_skies_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
ACTIVE_USERS = Gauge('outer_skies_active_users', 'Number of active users')
SYSTEM_MEMORY = Gauge('outer_skies_system_memory_bytes', 'System memory usage')
SYSTEM_CPU = Gauge('outer_skies_system_cpu_percent', 'System CPU usage')
DATABASE_CONNECTIONS = Gauge('outer_skies_database_connections', 'Database connections')
CACHE_HIT_RATIO = Gauge('outer_skies_cache_hit_ratio', 'Cache hit ratio')
ERROR_RATE = Counter('outer_skies_errors_total', 'Total errors', ['type', 'severity'])
SUBSCRIPTION_REVENUE = Counter('outer_skies_subscription_revenue', 'Subscription revenue', ['plan'])

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io: Dict[str, float]
    load_average: List[float]
    uptime: float

@dataclass
class ApplicationMetrics:
    """Application performance metrics"""
    timestamp: datetime
    request_count: int
    error_count: int
    avg_response_time: float
    active_connections: int
    cache_hit_ratio: float
    database_queries: int
    slow_queries: int

@dataclass
class BusinessMetrics:
    """Business performance metrics"""
    timestamp: datetime
    active_users: int
    new_registrations: int
    subscription_revenue: float
    chart_generations: int
    api_calls: int
    conversion_rate: float

class ProductionMonitor:
    """
    Comprehensive production monitoring system
    """
    
    def __init__(self):
        self.metrics_history = {
            'system': deque(maxlen=1000),
            'application': deque(maxlen=1000),
            'business': deque(maxlen=1000)
        }
        self.alerts = []
        self.alert_thresholds = {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'disk_usage_percent': 90.0,
            'error_rate': 5.0,
            'response_time': 2.0,
            'cache_hit_ratio': 70.0
        }
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Initialize Sentry for error tracking
        if hasattr(settings, 'SENTRY_DSN'):
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[DjangoIntegration()],
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
            )
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Production monitoring started")
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join()
        logger.info("Production monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect all metrics
                system_metrics = self.collect_system_metrics()
                app_metrics = self.collect_application_metrics()
                business_metrics = self.collect_business_metrics()
                
                # Store metrics
                self.metrics_history['system'].append(system_metrics)
                self.metrics_history['application'].append(app_metrics)
                self.metrics_history['business'].append(business_metrics)
                
                # Update Prometheus metrics
                self._update_prometheus_metrics(system_metrics, app_metrics, business_metrics)
                
                # Check for alerts
                self._check_alerts(system_metrics, app_metrics, business_metrics)
                
                # Sleep for monitoring interval
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect system-level metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            load_avg = psutil.getloadavg()
            uptime = time.time() - psutil.boot_time()
            
            metrics = SystemMetrics(
                timestamp=timezone.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_io={
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                load_average=list(load_avg),
                uptime=uptime
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=timezone.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                disk_usage_percent=0.0,
                network_io={},
                load_average=[0.0, 0.0, 0.0],
                uptime=0.0
            )
    
    def collect_application_metrics(self) -> ApplicationMetrics:
        """Collect application-level metrics"""
        try:
            # Get database connection info
            db_connections = len(connection.queries) if connection.queries else 0
            
            # Get cache statistics
            cache_stats = cache.get('cache_stats', {})
            cache_hits = cache_stats.get('hits', 0)
            cache_misses = cache_stats.get('misses', 0)
            cache_hit_ratio = (cache_hits / (cache_hits + cache_misses)) * 100 if (cache_hits + cache_misses) > 0 else 0
            
            # Get request statistics from middleware
            request_stats = cache.get('request_stats', {})
            request_count = request_stats.get('total_requests', 0)
            error_count = request_stats.get('errors', 0)
            avg_response_time = request_stats.get('avg_response_time', 0.0)
            
            # Count slow queries
            slow_queries = len([q for q in connection.queries if float(q.get('time', 0)) > 1.0]) if connection.queries else 0
            
            metrics = ApplicationMetrics(
                timestamp=timezone.now(),
                request_count=request_count,
                error_count=error_count,
                avg_response_time=avg_response_time,
                active_connections=db_connections,
                cache_hit_ratio=cache_hit_ratio,
                database_queries=db_connections,
                slow_queries=slow_queries
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            return ApplicationMetrics(
                timestamp=timezone.now(),
                request_count=0,
                error_count=0,
                avg_response_time=0.0,
                active_connections=0,
                cache_hit_ratio=0.0,
                database_queries=0,
                slow_queries=0
            )
    
    def collect_business_metrics(self) -> BusinessMetrics:
        """Collect business-level metrics"""
        try:
            from chart.models import Chart
            from payments.models import Subscription
            
            # Get active users (users with activity in last 24 hours)
            from django.contrib.auth.models import User
            from django.utils import timezone
            from datetime import timedelta
            
            active_users = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # Get new registrations in last 24 hours
            new_registrations = User.objects.filter(
                date_joined__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # Get subscription revenue
            subscriptions = Subscription.objects.filter(
                status='active',
                created_at__gte=timezone.now() - timedelta(days=30)
            )
            subscription_revenue = sum(sub.amount for sub in subscriptions)
            
            # Get chart generations in last 24 hours
            chart_generations = Chart.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
            
            # Get API calls from cache
            api_stats = cache.get('api_stats', {})
            api_calls = api_stats.get('total_calls', 0)
            
            # Calculate conversion rate
            total_visitors = cache.get('total_visitors', 0)
            conversion_rate = (new_registrations / total_visitors * 100) if total_visitors > 0 else 0
            
            metrics = BusinessMetrics(
                timestamp=timezone.now(),
                active_users=active_users,
                new_registrations=new_registrations,
                subscription_revenue=subscription_revenue,
                chart_generations=chart_generations,
                api_calls=api_calls,
                conversion_rate=conversion_rate
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting business metrics: {e}")
            return BusinessMetrics(
                timestamp=timezone.now(),
                active_users=0,
                new_registrations=0,
                subscription_revenue=0.0,
                chart_generations=0,
                api_calls=0,
                conversion_rate=0.0
            )
    
    def _update_prometheus_metrics(self, system_metrics: SystemMetrics, 
                                 app_metrics: ApplicationMetrics, 
                                 business_metrics: BusinessMetrics):
        """Update Prometheus metrics"""
        try:
            SYSTEM_CPU.set(system_metrics.cpu_percent)
            SYSTEM_MEMORY.set(system_metrics.memory_percent)
            DATABASE_CONNECTIONS.set(app_metrics.active_connections)
            CACHE_HIT_RATIO.set(app_metrics.cache_hit_ratio)
            ACTIVE_USERS.set(business_metrics.active_users)
            
        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {e}")
    
    def _check_alerts(self, system_metrics: SystemMetrics, 
                     app_metrics: ApplicationMetrics, 
                     business_metrics: BusinessMetrics):
        """Check for alert conditions"""
        alerts = []
        
        # System alerts
        if system_metrics.cpu_percent > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'system',
                'severity': 'warning',
                'message': f"High CPU usage: {system_metrics.cpu_percent}%",
                'timestamp': timezone.now()
            })
        
        if system_metrics.memory_percent > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'system',
                'severity': 'warning',
                'message': f"High memory usage: {system_metrics.memory_percent}%",
                'timestamp': timezone.now()
            })
        
        if system_metrics.disk_usage_percent > self.alert_thresholds['disk_usage_percent']:
            alerts.append({
                'type': 'system',
                'severity': 'critical',
                'message': f"High disk usage: {system_metrics.disk_usage_percent}%",
                'timestamp': timezone.now()
            })
        
        # Application alerts
        if app_metrics.avg_response_time > self.alert_thresholds['response_time']:
            alerts.append({
                'type': 'application',
                'severity': 'warning',
                'message': f"Slow response time: {app_metrics.avg_response_time}s",
                'timestamp': timezone.now()
            })
        
        if app_metrics.cache_hit_ratio < self.alert_thresholds['cache_hit_ratio']:
            alerts.append({
                'type': 'application',
                'severity': 'warning',
                'message': f"Low cache hit ratio: {app_metrics.cache_hit_ratio}%",
                'timestamp': timezone.now()
            })
        
        # Send alerts
        for alert in alerts:
            self._send_alert(alert)
            self.alerts.append(alert)
    
    def _send_alert(self, alert: Dict[str, Any]):
        """Send alert notification"""
        try:
            if hasattr(settings, 'ALERT_EMAIL_RECIPIENTS'):
                subject = f"Outer Skies Alert: {alert['type'].title()} - {alert['severity'].upper()}"
                message = f"""
Alert Details:
- Type: {alert['type']}
- Severity: {alert['severity']}
- Message: {alert['message']}
- Timestamp: {alert['timestamp']}

System Status:
- CPU: {self.metrics_history['system'][-1].cpu_percent if self.metrics_history['system'] else 'N/A'}%
- Memory: {self.metrics_history['system'][-1].memory_percent if self.metrics_history['system'] else 'N/A'}%
- Response Time: {self.metrics_history['application'][-1].avg_response_time if self.metrics_history['application'] else 'N/A'}s
                """
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=settings.ALERT_EMAIL_RECIPIENTS,
                    fail_silently=True
                )
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the specified time period"""
        try:
            cutoff_time = timezone.now() - timedelta(hours=hours)
            
            # Filter metrics by time
            system_metrics = [m for m in self.metrics_history['system'] if m.timestamp >= cutoff_time]
            app_metrics = [m for m in self.metrics_history['application'] if m.timestamp >= cutoff_time]
            business_metrics = [m for m in self.metrics_history['business'] if m.timestamp >= cutoff_time]
            
            if not system_metrics or not app_metrics or not business_metrics:
                return {}
            
            summary = {
                'system': {
                    'avg_cpu': sum(m.cpu_percent for m in system_metrics) / len(system_metrics),
                    'max_cpu': max(m.cpu_percent for m in system_metrics),
                    'avg_memory': sum(m.memory_percent for m in system_metrics) / len(system_metrics),
                    'max_memory': max(m.memory_percent for m in system_metrics),
                    'avg_disk': sum(m.disk_usage_percent for m in system_metrics) / len(system_metrics),
                    'max_disk': max(m.disk_usage_percent for m in system_metrics),
                },
                'application': {
                    'total_requests': sum(m.request_count for m in app_metrics),
                    'total_errors': sum(m.error_count for m in app_metrics),
                    'avg_response_time': sum(m.avg_response_time for m in app_metrics) / len(app_metrics),
                    'max_response_time': max(m.avg_response_time for m in app_metrics),
                    'avg_cache_hit_ratio': sum(m.cache_hit_ratio for m in app_metrics) / len(app_metrics),
                    'total_slow_queries': sum(m.slow_queries for m in app_metrics),
                },
                'business': {
                    'avg_active_users': sum(m.active_users for m in business_metrics) / len(business_metrics),
                    'max_active_users': max(m.active_users for m in business_metrics),
                    'total_registrations': sum(m.new_registrations for m in business_metrics),
                    'total_revenue': sum(m.subscription_revenue for m in business_metrics),
                    'total_chart_generations': sum(m.chart_generations for m in business_metrics),
                    'total_api_calls': sum(m.api_calls for m in business_metrics),
                    'avg_conversion_rate': sum(m.conversion_rate for m in business_metrics) / len(business_metrics),
                },
                'alerts': [alert for alert in self.alerts if alert['timestamp'] >= cutoff_time]
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {}
    
    def get_prometheus_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        try:
            return generate_latest()
        except Exception as e:
            logger.error(f"Error generating Prometheus metrics: {e}")
            return ""
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format"""
        try:
            if format == 'json':
                return json.dumps({
                    'system': [asdict(m) for m in self.metrics_history['system']],
                    'application': [asdict(m) for m in self.metrics_history['application']],
                    'business': [asdict(m) for m in self.metrics_history['business']],
                    'alerts': self.alerts
                }, default=str)
            elif format == 'prometheus':
                return self.get_prometheus_metrics()
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return ""

# Global monitor instance
production_monitor = ProductionMonitor() 