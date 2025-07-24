from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .task_views import (
    start_chart_generation, start_interpretation_generation, start_plugin_processing,
    get_task_status_view, cancel_task_view, get_task_result, delete_task, list_user_tasks
)
from .enhanced_task_views import (
    submit_enhanced_task, get_enhanced_task_status, cancel_enhanced_task,
    retry_enhanced_task, list_user_enhanced_tasks, get_queue_statistics,
    cleanup_old_tasks, get_dead_letter_queue, reprocess_dead_letter_task, bulk_task_operations
)
from .monitoring_views import (
    system_health, metrics_summary, security_report, prometheus_metrics,
    business_metrics, start_monitoring, stop_monitoring, monitoring_status,
    export_metrics, alert_history, block_ip, threat_indicators
)

# Import Priority 3 security endpoints
from api.security.enhanced_auth import (
    enhanced_register, enhanced_login, setup_two_factor,
    verify_two_factor_setup, get_sessions, logout_session
)
from api.docs.enhanced_api_docs import (
    api_documentation, security_documentation, rate_limit_info,
    api_status, error_codes, code_examples
)

# Create router and register viewsets
router = DefaultRouter()
# Basenames are required for correct route names in tests
router.register(r'auth', views.AuthViewSet, basename='auth')
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'charts', views.ChartViewSet, basename='charts')
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscriptions')
router.register(r'payments', views.PaymentViewSet, basename='payments')
router.register(r'coupons', views.CouponViewSet, basename='coupons')
router.register(r'chat', views.ChatViewSet, basename='chat')
router.register(r'system', views.SystemViewSet, basename='system')

# Task management routes
router.register(r'background-charts', views.BackgroundChartViewSet, basename='background-chart')

# System endpoints:
#   /api/v1/system/health/         - Comprehensive health check
#   /api/v1/system/quick_health/   - Quick health check for load balancers
#   /api/v1/system/performance/    - Performance summary

urlpatterns = [
    path('', include(router.urls)),
    
    # Background Task Management Endpoints
    path('tasks/start-chart/', start_chart_generation, name='start_chart_generation'),
    path('tasks/start-interpretation/', start_interpretation_generation, name='start_interpretation_generation'),
    path('tasks/start-plugin/', start_plugin_processing, name='start_plugin_processing'),
    path('tasks/<str:task_id>/status/', get_task_status_view, name='get_task_status'),
    path('tasks/<str:task_id>/cancel/', cancel_task_view, name='cancel_task'),
    path('tasks/<str:task_id>/result/', get_task_result, name='get_task_result'),
    path('tasks/<str:task_id>/delete/', delete_task, name='delete_task'),
    path('tasks/', list_user_tasks, name='list_user_tasks'),
    
    # Priority 3 Enhanced Authentication Endpoints
    path('auth/enhanced-register/', enhanced_register, name='enhanced_register'),
    path('auth/enhanced-login/', enhanced_login, name='enhanced_login'),
    path('auth/setup-2fa/', setup_two_factor, name='setup_2fa'),
    path('auth/verify-2fa/', verify_two_factor_setup, name='verify_2fa'),
    path('auth/sessions/', get_sessions, name='get_sessions'),
    path('auth/logout-session/', logout_session, name='logout_session'),
    
    # Priority 3 Documentation & Security Info Endpoints
    path('docs/', api_documentation, name='api_docs'),
    path('security/', security_documentation, name='security_docs'),
    path('rate-limits/', rate_limit_info, name='rate_limit_info'),
    path('status/', api_status, name='api_status'),
    path('error-codes/', error_codes, name='error_codes'),
    path('code-examples/', code_examples, name='code_examples'),
    
    # Enhanced Task Management Endpoints
    path('tasks/enhanced/submit/', submit_enhanced_task, name='submit_enhanced_task'),
    path('tasks/enhanced/<str:task_id>/status/', get_enhanced_task_status, name='get_enhanced_task_status'),
    path('tasks/enhanced/<str:task_id>/cancel/', cancel_enhanced_task, name='cancel_enhanced_task'),
    path('tasks/enhanced/<str:task_id>/retry/', retry_enhanced_task, name='retry_enhanced_task'),
    path('tasks/enhanced/user/', list_user_enhanced_tasks, name='list_user_enhanced_tasks'),
    path('tasks/enhanced/queue-stats/', get_queue_statistics, name='get_queue_statistics'),
    path('tasks/enhanced/cleanup/', cleanup_old_tasks, name='cleanup_old_tasks'),
    path('tasks/enhanced/dead-letter/', get_dead_letter_queue, name='get_dead_letter_queue'),
    path('tasks/enhanced/dead-letter/<str:task_id>/reprocess/', reprocess_dead_letter_task, name='reprocess_dead_letter_task'),
    path('tasks/enhanced/bulk/', bulk_task_operations, name='bulk_task_operations'),

    # Phase 3: Monitoring and Security endpoints
    path('monitoring/health/', system_health, name='system-health'),
    path('monitoring/metrics/', metrics_summary, name='metrics-summary'),
    path('monitoring/security/', security_report, name='security-report'),
    path('monitoring/prometheus/', prometheus_metrics, name='prometheus-metrics'),
    path('monitoring/business/', business_metrics, name='business-metrics'),
    path('monitoring/start/', start_monitoring, name='start-monitoring'),
    path('monitoring/stop/', stop_monitoring, name='stop-monitoring'),
    path('monitoring/status/', monitoring_status, name='monitoring-status'),
    path('monitoring/export/', export_metrics, name='export-metrics'),
    path('monitoring/alerts/', alert_history, name='alert-history'),
    path('security/block-ip/', block_ip, name='block-ip'),
    path('security/threats/', threat_indicators, name='threat-indicators'),
]
