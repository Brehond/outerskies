from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

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
] 