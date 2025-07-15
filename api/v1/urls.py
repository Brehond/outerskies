from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

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
router.register(r'tasks', views.TaskStatusViewSet, basename='task')
router.register(r'background-charts', views.BackgroundChartViewSet, basename='background-chart')

# System endpoints:
#   /api/v1/system/health/         - Comprehensive health check
#   /api/v1/system/quick_health/   - Quick health check for load balancers
#   /api/v1/system/performance/    - Performance summary

urlpatterns = [
    path('', include(router.urls)),
    
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
]
