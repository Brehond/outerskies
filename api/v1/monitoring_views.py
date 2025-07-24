"""
Monitoring API Views for Outer Skies
Provides access to production metrics, security reports, and system health
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views import View
from django.core.cache import cache
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from api.services.api_standardizer import APIStandardizer
from monitoring.production_monitor import production_monitor
from api.security.advanced_security import advanced_security

logger = logging.getLogger(__name__)

def is_admin_user(user):
    """Check if user is admin"""
    return user.is_authenticated and user.is_staff

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def system_health(request):
    """Get system health status"""
    try:
        # Get basic system metrics
        system_metrics = production_monitor.collect_system_metrics()
        app_metrics = production_monitor.collect_application_metrics()
        
        # Determine overall health status
        health_status = 'healthy'
        issues = []
        
        if system_metrics.cpu_percent > 80:
            health_status = 'warning'
            issues.append('High CPU usage')
        
        if system_metrics.memory_percent > 85:
            health_status = 'warning'
            issues.append('High memory usage')
        
        if system_metrics.disk_usage_percent > 90:
            health_status = 'critical'
            issues.append('High disk usage')
        
        if app_metrics.avg_response_time > 2.0:
            health_status = 'warning'
            issues.append('Slow response time')
        
        if app_metrics.cache_hit_ratio < 70:
            health_status = 'warning'
            issues.append('Low cache hit ratio')
        
        # Check database connectivity
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_status = 'healthy'
        except Exception as e:
            db_status = 'error'
            health_status = 'critical'
            issues.append('Database connectivity issue')
        
        # Check cache connectivity
        try:
            cache.set('health_check', 'ok', timeout=10)
            cache_status = 'healthy'
        except Exception as e:
            cache_status = 'error'
            health_status = 'critical'
            issues.append('Cache connectivity issue')
        
        response_data = {
            'status': health_status,
            'timestamp': timezone.now().isoformat(),
            'issues': issues,
            'components': {
                'system': {
                    'cpu_percent': system_metrics.cpu_percent,
                    'memory_percent': system_metrics.memory_percent,
                    'disk_usage_percent': system_metrics.disk_usage_percent,
                    'load_average': system_metrics.load_average
                },
                'application': {
                    'avg_response_time': app_metrics.avg_response_time,
                    'cache_hit_ratio': app_metrics.cache_hit_ratio,
                    'active_connections': app_metrics.active_connections,
                    'slow_queries': app_metrics.slow_queries
                },
                'database': {
                    'status': db_status
                },
                'cache': {
                    'status': cache_status
                }
            }
        }
        
        return APIStandardizer.success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return APIStandardizer.error_response(
            "Failed to get system health",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def metrics_summary(request):
    """Get metrics summary for specified time period"""
    try:
        hours = int(request.GET.get('hours', 24))
        if hours > 168:  # Max 7 days
            hours = 168
        
        summary = production_monitor.get_metrics_summary(hours)
        
        if not summary:
            return APIStandardizer.error_response(
                "No metrics available for specified time period",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return APIStandardizer.success_response(summary)
        
    except ValueError:
        return APIStandardizer.error_response(
            "Invalid hours parameter",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return APIStandardizer.error_response(
            "Failed to get metrics summary",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def security_report(request):
    """Get security report for specified time period"""
    try:
        hours = int(request.GET.get('hours', 24))
        if hours > 168:  # Max 7 days
            hours = 168
        
        report = advanced_security.get_security_report(hours)
        
        return APIStandardizer.success_response(report)
        
    except ValueError:
        return APIStandardizer.error_response(
            "Invalid hours parameter",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting security report: {e}")
        return APIStandardizer.error_response(
            "Failed to get security report",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def prometheus_metrics(request):
    """Get Prometheus metrics"""
    try:
        metrics = production_monitor.get_prometheus_metrics()
        
        if not metrics:
            return APIStandardizer.error_response(
                "No Prometheus metrics available",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        response = Response(metrics, content_type='text/plain')
        return response
        
    except Exception as e:
        logger.error(f"Error getting Prometheus metrics: {e}")
        return APIStandardizer.error_response(
            "Failed to get Prometheus metrics",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def business_metrics(request):
    """Get business performance metrics"""
    try:
        # Get business metrics
        business_metrics = production_monitor.collect_business_metrics()
        
        # Get additional business data
        from chart.models import Chart
        from payments.models import Subscription
        from django.contrib.auth.models import User
        
        # Revenue metrics
        total_revenue = Subscription.objects.filter(
            status='active'
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        monthly_revenue = Subscription.objects.filter(
            status='active',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        # User metrics
        total_users = User.objects.count()
        active_users_7d = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Chart metrics
        total_charts = Chart.objects.count()
        charts_24h = Chart.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        # Conversion metrics
        registrations_24h = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(hours=24)
        ).count()
        
        total_visitors = cache.get('total_visitors', 0)
        conversion_rate = (registrations_24h / total_visitors * 100) if total_visitors > 0 else 0
        
        response_data = {
            'current_metrics': {
                'active_users': business_metrics.active_users,
                'new_registrations': business_metrics.new_registrations,
                'subscription_revenue': business_metrics.subscription_revenue,
                'chart_generations': business_metrics.chart_generations,
                'api_calls': business_metrics.api_calls,
                'conversion_rate': business_metrics.conversion_rate
            },
            'cumulative_metrics': {
                'total_revenue': total_revenue,
                'monthly_revenue': monthly_revenue,
                'total_users': total_users,
                'active_users_7d': active_users_7d,
                'total_charts': total_charts,
                'charts_24h': charts_24h
            },
            'performance_metrics': {
                'conversion_rate_24h': conversion_rate,
                'revenue_per_user': total_revenue / total_users if total_users > 0 else 0,
                'charts_per_user': total_charts / total_users if total_users > 0 else 0
            }
        }
        
        return APIStandardizer.success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting business metrics: {e}")
        return APIStandardizer.error_response(
            "Failed to get business metrics",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def start_monitoring(request):
    """Start production monitoring"""
    try:
        production_monitor.start_monitoring()
        
        return APIStandardizer.success_response({
            'message': 'Production monitoring started successfully',
            'status': 'active'
        })
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return APIStandardizer.error_response(
            "Failed to start monitoring",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def stop_monitoring(request):
    """Stop production monitoring"""
    try:
        production_monitor.stop_monitoring()
        
        return APIStandardizer.success_response({
            'message': 'Production monitoring stopped successfully',
            'status': 'inactive'
        })
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return APIStandardizer.error_response(
            "Failed to stop monitoring",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def monitoring_status(request):
    """Get monitoring system status"""
    try:
        status_data = {
            'monitoring_active': production_monitor.monitoring_active,
            'metrics_history_size': {
                'system': len(production_monitor.metrics_history['system']),
                'application': len(production_monitor.metrics_history['application']),
                'business': len(production_monitor.metrics_history['business'])
            },
            'alerts_count': len(production_monitor.alerts),
            'security_events_count': len(advanced_security.security_events),
            'threat_indicators_count': len(advanced_security.threat_indicators),
            'blocked_ips_count': len(advanced_security.blocked_ips)
        }
        
        return APIStandardizer.success_response(status_data)
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return APIStandardizer.error_response(
            "Failed to get monitoring status",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def export_metrics(request):
    """Export metrics in specified format"""
    try:
        format_type = request.GET.get('format', 'json')
        
        if format_type not in ['json', 'prometheus']:
            return APIStandardizer.error_response(
                "Invalid format. Supported formats: json, prometheus",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        metrics_data = production_monitor.export_metrics(format_type)
        
        if not metrics_data:
            return APIStandardizer.error_response(
                "No metrics available for export",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if format_type == 'prometheus':
            response = Response(metrics_data, content_type='text/plain')
        else:
            response = Response(metrics_data, content_type='application/json')
        
        response['Content-Disposition'] = f'attachment; filename="metrics_{format_type}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.{format_type}"'
        return response
        
    except Exception as e:
        logger.error(f"Error exporting metrics: {e}")
        return APIStandardizer.error_response(
            "Failed to export metrics",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def alert_history(request):
    """Get alert history"""
    try:
        hours = int(request.GET.get('hours', 24))
        if hours > 168:  # Max 7 days
            hours = 168
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        recent_alerts = [
            alert for alert in production_monitor.alerts 
            if alert['timestamp'] >= cutoff_time
        ]
        
        # Group alerts by type and severity
        alert_summary = {}
        for alert in recent_alerts:
            alert_type = alert['type']
            severity = alert['severity']
            
            if alert_type not in alert_summary:
                alert_summary[alert_type] = {}
            
            if severity not in alert_summary[alert_type]:
                alert_summary[alert_type][severity] = 0
            
            alert_summary[alert_type][severity] += 1
        
        response_data = {
            'period_hours': hours,
            'total_alerts': len(recent_alerts),
            'alert_summary': alert_summary,
            'recent_alerts': recent_alerts[-50:]  # Last 50 alerts
        }
        
        return APIStandardizer.success_response(response_data)
        
    except ValueError:
        return APIStandardizer.error_response(
            "Invalid hours parameter",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        return APIStandardizer.error_response(
            "Failed to get alert history",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def block_ip(request):
    """Block an IP address"""
    try:
        ip_address = request.data.get('ip_address')
        reason = request.data.get('reason', 'Manual block')
        
        if not ip_address:
            return APIStandardizer.error_response(
                "IP address is required",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        advanced_security.block_ip(ip_address, reason)
        
        return APIStandardizer.success_response({
            'message': f'IP {ip_address} blocked successfully',
            'reason': reason,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error blocking IP: {e}")
        return APIStandardizer.error_response(
            "Failed to block IP",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def threat_indicators(request):
    """Get threat indicators"""
    try:
        # Get top threat indicators
        top_threats = sorted(
            advanced_security.threat_indicators.values(),
            key=lambda x: x.confidence,
            reverse=True
        )[:50]  # Top 50 threats
        
        threat_data = [
            {
                'ip_address': threat.ip_address,
                'threat_type': threat.threat_type,
                'confidence': threat.confidence,
                'event_count': threat.event_count,
                'first_seen': threat.first_seen.isoformat(),
                'last_seen': threat.last_seen.isoformat(),
                'details': threat.details
            }
            for threat in top_threats
        ]
        
        response_data = {
            'total_threats': len(advanced_security.threat_indicators),
            'top_threats': threat_data,
            'blocked_ips': list(advanced_security.blocked_ips)
        }
        
        return APIStandardizer.success_response(response_data)
        
    except Exception as e:
        logger.error(f"Error getting threat indicators: {e}")
        return APIStandardizer.error_response(
            "Failed to get threat indicators",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ) 