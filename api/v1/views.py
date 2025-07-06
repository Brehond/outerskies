import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiTypes

from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    ChartSerializer, ChartGenerationSerializer, ChartInterpretationSerializer,
    SubscriptionPlanSerializer, UserSubscriptionSerializer, PaymentSerializer,
    CouponSerializer, ChatSessionSerializer, ChatMessageSerializer,
    KnowledgeDocumentSerializer, AIModelSerializer, ThemeSerializer,
    TaskStatusSerializer
)
from api.utils import success_response, error_response, validate_required_fields
from chart.models import User, Chart, TaskStatus
from chart.services.ephemeris import get_chart_data
from chart.services.caching import ephemeris_cache, ai_cache, user_cache, cache_service
from chart.views import (
    local_to_utc, validate_input, calculate_chart_data_with_caching,
    generate_planet_interpretations_with_caching, generate_master_interpretation_with_caching
)
from payments.models import SubscriptionPlan, UserSubscription, Payment, Coupon
from payments.stripe_utils import StripeService
from ai_integration.openrouter_api import get_available_models, generate_interpretation
from astrology_ai.context_processors import theme_context
from chart.tasks import generate_chart_task, generate_interpretation_task, calculate_ephemeris_task
from celery.result import AsyncResult
from chart.celery_utils import enhanced_celery_manager
from api.middleware.enhanced_rate_limit import UsageAnalytics
from monitoring.health_checks import get_system_health, get_quick_health_status
from monitoring.performance_monitor import get_performance_summary

# Import chat models if they exist
try:
    from plugins.astrology_chat.models import ChatSession, ChatMessage, KnowledgeDocument
    CHAT_AVAILABLE = True
except ImportError:
    CHAT_AVAILABLE = False
    ChatSession = None
    ChatMessage = None
    KnowledgeDocument = None

logger = logging.getLogger(__name__)


class APIKeyOrJWTPermission(permissions.BasePermission):
    """
    Custom permission class that allows authentication via either JWT token or API key.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated via JWT
        if request.user and request.user.is_authenticated:
            return True
            
        # Check if API key is provided and valid
        api_key = request.headers.get('X-API-Key')
        if api_key:
            from django.conf import settings
            if api_key == getattr(settings, 'API_KEY', ''):
                return True
                
        return False


@extend_schema_view(
    register=extend_schema(
        summary="Register new user",
        description="Create a new user account and return authentication tokens",
        tags=["authentication"],
        examples=[
            OpenApiExample(
                "Successful Registration",
                value={
                    "username": "johndoe",
                    "email": "john@example.com",
                    "password": "securepassword123",
                    "password_confirm": "securepassword123",
                    "first_name": "John",
                    "last_name": "Doe"
                },
                status_codes=["201"]
            )
        ]
    ),
    login=extend_schema(
        summary="User login",
        description="Authenticate user and return access tokens",
        tags=["authentication"],
        examples=[
            OpenApiExample(
                "Successful Login",
                value={
                    "username": "johndoe",
                    "password": "securepassword123"
                },
                status_codes=["200"]
            )
        ]
    ),
    refresh=extend_schema(
        summary="Refresh access token",
        description="Get a new access token using a refresh token",
        tags=["authentication"]
    ),
    logout=extend_schema(
        summary="User logout",
        description="Invalidate refresh token and logout user",
        tags=["authentication"]
    )
)
class AuthViewSet(viewsets.ViewSet):
    """Authentication endpoints"""
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer  # Default serializer for documentation
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """User registration endpoint"""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return success_response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, "User registered successfully")
        return error_response("Registration failed", data=serializer.errors)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """User login endpoint"""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return success_response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, "Login successful")
        return error_response("Login failed", data=serializer.errors)
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Refresh token endpoint"""
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return error_response("Refresh token is required")
            
            refresh = RefreshToken(refresh_token)
            return success_response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, "Token refreshed successfully")
        except Exception as e:
            return error_response("Invalid refresh token")
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """User logout endpoint"""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return success_response(message="Logout successful")
        except Exception as e:
            return error_response("Logout failed")


@extend_schema_view(
    profile=extend_schema(
        summary="Get user profile",
        description="Retrieve current user's profile information",
        tags=["users"]
    ),
    update_profile=extend_schema(
        summary="Update user profile",
        description="Update current user's profile information",
        tags=["users"]
    ),
    change_password=extend_schema(
        summary="Change password",
        description="Change user's password",
        tags=["users"]
    )
)
class UserViewSet(viewsets.ModelViewSet):
    """User management endpoints"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
    
    def list(self, request, *args, **kwargs):
        """List users (returns current user only)"""
        return self.retrieve(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """Get current user"""
        return success_response(UserSerializer(request.user).data)
    
    @action(detail=False, methods=['get'], name='users-profile')
    def profile(self, request):
        """Get user profile with cached preferences"""
        user_data = UserSerializer(request.user).data
        
        # Get cached user preferences
        cached_preferences = user_cache.get_user_preferences(request.user.id)
        if cached_preferences:
            user_data['cached_preferences'] = cached_preferences
        
        return success_response(user_data)
    
    @action(detail=False, methods=['put', 'patch'], name='users-update-profile')
    def update_profile(self, request):
        """Update user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            
            # Cache updated preferences
            user_cache.cache_user_preferences(user.id, {
                'preferred_zodiac_type': user.preferred_zodiac_type,
                'preferred_house_system': user.preferred_house_system,
                'preferred_ai_model': user.preferred_ai_model,
                'timezone': user.timezone
            })
            
            return success_response(UserSerializer(user).data, "Profile updated successfully")
        return error_response("Profile update failed", data=serializer.errors)
    
    @action(detail=False, methods=['post'], name='users-change-password')
    def change_password(self, request):
        """Change user password"""
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return error_response("Old password and new password are required")
        
        if not request.user.check_password(old_password):
            return error_response("Invalid old password")
        
        request.user.set_password(new_password)
        request.user.save()
        
        return success_response(message="Password changed successfully")


@extend_schema_view(
    generate=extend_schema(
        summary="Generate astrological chart",
        description="Generate a new astrological birth chart with AI interpretation",
        tags=["charts"],
        examples=[
            OpenApiExample(
                "Chart Generation Request",
                value={
                    "birth_date": "1990-05-15",
                    "birth_time": "14:30",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_name": "New York, NY",
                    "timezone": "America/New_York",
                    "zodiac_type": "tropical",
                    "house_system": "placidus",
                    "ai_model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "interpretation_type": "comprehensive",
                    "chart_name": "My Birth Chart"
                },
                status_codes=["201"]
            )
        ]
    ),
    interpret=extend_schema(
        summary="Generate chart interpretation",
        description="Generate AI interpretation for an existing chart",
        tags=["interpretations"]
    ),
    toggle_favorite=extend_schema(
        summary="Toggle chart favorite",
        description="Mark or unmark a chart as favorite",
        tags=["charts"]
    ),
    favorites=extend_schema(
        summary="List favorite charts",
        description="Get all charts marked as favorite by the user",
        tags=["charts"]
    )
)
class ChartViewSet(viewsets.ModelViewSet):
    """Chart management endpoints"""
    serializer_class = ChartSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Chart.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        """List user charts with caching"""
        # Try to get cached chart summary
        cached_summary = user_cache.get_user_charts_summary(request.user.id)
        if cached_summary:
            return success_response(cached_summary)
        
        # Get charts from database
        charts = self.get_queryset()
        serializer = self.get_serializer(charts, many=True)
        
        # Cache the summary
        user_cache.cache_user_charts_summary(request.user.id, {
            'charts': serializer.data,
            'total_count': charts.count(),
            'cached_at': timezone.now().isoformat()
        })
        
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Get specific chart"""
        chart = self.get_object()
        return success_response(ChartSerializer(chart).data)
    
    @action(detail=False, methods=['post'], name='charts-generate')
    def generate(self, request):
        """Generate new chart with caching"""
        serializer = ChartGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("Invalid chart data", data=serializer.errors)
        
        data = serializer.validated_data
        
        try:
            # Convert local time to UTC
            utc_date, utc_time = local_to_utc(
                data['birth_date'], data['birth_time'], data['timezone']
            )
            
            # Calculate chart data with caching
            chart_data, error = calculate_chart_data_with_caching(
                utc_date, utc_time, data['latitude'], data['longitude'],
                data['zodiac_type'], data['house_system'], data['timezone']
            )
            
            if error:
                return error_response(f"Chart calculation failed: {error}")
            
            # Generate interpretations with caching
            planet_interpretations = generate_planet_interpretations_with_caching(
                chart_data, utc_date, utc_time, data['location_name'],
                data['ai_model'], data['temperature'], data['max_tokens']
            )
            
            master_interpretation = generate_master_interpretation_with_caching(
                chart_data, utc_date, utc_time, data['location_name'],
                data['ai_model'], data['temperature'], data['max_tokens']
            )
            
            # Create chart record
            chart = Chart.objects.create(
                user=request.user,
                name=data.get('chart_name', ''),
                birth_date=data['birth_date'],
                birth_time=data['birth_time'],
                latitude=data['latitude'],
                longitude=data['longitude'],
                location_name=data['location_name'],
                timezone=data['timezone'],
                zodiac_type=data['zodiac_type'],
                house_system=data['house_system'],
                ai_model_used=data['ai_model'],
                chart_data=chart_data,
                planetary_positions=chart_data.get('planetary_positions', {}),
                house_positions=chart_data.get('house_positions', {}),
                aspects=chart_data.get('aspects', {}),
                interpretation=master_interpretation
            )
            
            # Clear user's cached chart summary
            user_cache.delete('user_session', f"{request.user.id}_charts")
            
            return success_response(ChartSerializer(chart).data, "Chart generated successfully")
            
        except Exception as e:
            logger.error(f"Chart generation error: {e}")
            return error_response(f"Chart generation failed: {str(e)}")
    
    @action(detail=True, methods=['post'])
    @extend_schema(parameters=[OpenApiParameter("pk", OpenApiTypes.UUID, OpenApiParameter.PATH, description="Chart ID")])
    def interpret(self, request, pk=None):
        """Generate interpretation for existing chart"""
        chart = self.get_object()
        
        try:
            # Generate new interpretation with caching
            interpretation = generate_master_interpretation_with_caching(
                chart.chart_data, chart.birth_date, chart.birth_time,
                chart.location_name, chart.ai_model_used, 0.7, 1000
            )
            
            # Update chart
            chart.interpretation = interpretation
            chart.save()
            
            return success_response(ChartSerializer(chart).data, "Interpretation generated successfully")
            
        except Exception as e:
            logger.error(f"Interpretation generation error: {e}")
            return error_response(f"Interpretation generation failed: {str(e)}")
    
    @action(detail=True, methods=['post'])
    @extend_schema(parameters=[OpenApiParameter("pk", OpenApiTypes.UUID, OpenApiParameter.PATH, description="Chart ID")])
    def toggle_favorite(self, request, pk=None):
        """Toggle chart favorite status"""
        chart = self.get_object()
        chart.is_favorite = not chart.is_favorite
        chart.save()
        
        return success_response({
            'is_favorite': chart.is_favorite
        }, f"Chart {'marked as favorite' if chart.is_favorite else 'unmarked as favorite'}")
    
    @action(detail=False, methods=['get'])
    def favorites(self, request):
        """Get favorite charts"""
        favorites = self.get_queryset().filter(is_favorite=True)
        serializer = self.get_serializer(favorites, many=True)
        return success_response(serializer.data)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Subscription management endpoints"""
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data)
            return success_response(paginated_data.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response({'results': serializer.data})
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_subscription(self, request):
        """Get current user's subscription"""
        try:
            subscription = request.user.subscription
            serializer = UserSubscriptionSerializer(subscription)
            return success_response({'subscription': serializer.data})
        except UserSubscription.DoesNotExist:
            return error_response("No active subscription found")
    
    @action(detail=False, methods=['post'])
    def create_subscription(self, request):
        """Create a new subscription"""
        plan_id = request.data.get('plan_id')
        payment_method_id = request.data.get('payment_method_id')
        
        if not plan_id or not payment_method_id:
            return error_response("Plan ID and payment method ID are required")
        
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return error_response("Invalid plan")
        
        try:
            stripe_service = StripeService()
            subscription = stripe_service.create_subscription(
                user=request.user,
                plan=plan,
                payment_method_id=payment_method_id
            )
            return success_response(
                UserSubscriptionSerializer(subscription).data,
                "Subscription created successfully"
            )
        except Exception as e:
            logger.error(f"Subscription creation error: {e}")
            return error_response("Subscription creation failed")
    
    @action(detail=False, methods=['post'])
    def cancel_subscription(self, request):
        """Cancel current subscription"""
        try:
            subscription = request.user.subscription
            stripe_service = StripeService()
            stripe_service.cancel_subscription(subscription)
            return success_response(message="Subscription cancelled successfully")
        except UserSubscription.DoesNotExist:
            return error_response("No active subscription to cancel")
        except Exception as e:
            logger.error(f"Subscription cancellation error: {e}")
            return error_response("Subscription cancellation failed")


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Payment history endpoints"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_data = self.get_paginated_response(serializer.data)
            return success_response(paginated_data.data)
        serializer = self.get_serializer(queryset, many=True)
        return success_response({'results': serializer.data})
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)


class CouponViewSet(viewsets.ViewSet):
    """Coupon validation endpoints"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CouponSerializer
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Validate a coupon code"""
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            try:
                coupon = Coupon.objects.get(
                    code=serializer.validated_data['code'],
                    is_active=True
                )
                return success_response({
                    'code': coupon.code,
                    'name': coupon.name,
                    'description': coupon.description,
                    'discount_type': coupon.discount_type,
                    'discount_value': coupon.discount_value,
                    'currency': coupon.currency
                }, "Coupon is valid")
            except Coupon.DoesNotExist:
                return error_response("Invalid coupon code")
        return error_response("Invalid coupon data", data=serializer.errors)


class ChatViewSet(viewsets.ModelViewSet):
    """Chat session endpoints"""
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if not CHAT_AVAILABLE:
            return ChatSession.objects.none()
        return ChatSession.objects.filter(user=self.request.user)
    
    def list(self, request, *args, **kwargs):
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return super().create(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return super().retrieve(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    @extend_schema(parameters=[OpenApiParameter("pk", OpenApiTypes.UUID, OpenApiParameter.PATH, description="Chat Session ID")])
    def send_message(self, request, pk=None):
        """Send a message in a chat session"""
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            session = self.get_object()
        except ChatSession.DoesNotExist:
            return error_response("Chat session not found", status_code=status.HTTP_404_NOT_FOUND)
        
        message_content = request.data.get('content')
        if not message_content:
            return error_response("Message content is required")
        
        try:
            # Create user message
            user_message = ChatMessage.objects.create(
                session=session,
                user=request.user,
                content=message_content,
                message_type='user'
            )
            
            # Generate AI response (simplified - would integrate with AI service)
            ai_response = f"Thank you for your message: {message_content}. This is a placeholder AI response."
            
            ai_message = ChatMessage.objects.create(
                session=session,
                user=request.user,
                content=ai_response,
                message_type='ai',
                is_ai=True
            )
            
            return success_response({
                'user_message': ChatMessageSerializer(user_message).data,
                'ai_message': ChatMessageSerializer(ai_message).data
            }, "Message sent successfully")
            
        except Exception as e:
            logger.error(f"Chat message error: {e}")
            return error_response("Failed to send message")
    
    @action(detail=True, methods=['get'])
    @extend_schema(parameters=[OpenApiParameter("pk", OpenApiTypes.UUID, OpenApiParameter.PATH, description="Chat Session ID")])
    def messages(self, request, pk=None):
        """Get messages for a chat session"""
        if not CHAT_AVAILABLE:
            return error_response("Chat feature not available", status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        try:
            session = self.get_object()
            messages = session.chat_messages.all().order_by('created_at')
            serializer = ChatMessageSerializer(messages, many=True)
            return success_response(serializer.data)
        except ChatSession.DoesNotExist:
            return error_response("Chat session not found", status_code=status.HTTP_404_NOT_FOUND)


class SystemViewSet(viewsets.ViewSet):
    """System information endpoints"""
    permission_classes = [permissions.AllowAny]
    serializer_class = AIModelSerializer  # Default serializer for documentation
    
    @action(detail=False, methods=['get'])
    def ai_models(self, request):
        """Get available AI models"""
        model_data = [
            {
                'name': 'gpt-4',
                'id': 'gpt-4',
                'max_tokens': 4000,
                'temperature': 0.7,
                'description': 'AI model: gpt-4'
            },
            {
                'name': 'claude-3-opus',
                'id': 'claude-3-opus',
                'max_tokens': 4000,
                'temperature': 0.7,
                'description': 'AI model: claude-3-opus'
            },
            {
                'name': 'gpt-3.5-turbo',
                'id': 'gpt-3.5-turbo',
                'max_tokens': 2000,
                'temperature': 0.7,
                'description': 'AI model: gpt-3.5-turbo'
            }
        ]
        return success_response({'models': model_data})
    
    @action(detail=False, methods=['get'])
    def themes(self, request):
        """Get available themes"""
        # Get themes from context processor
        themes_data = []
        themes = theme_context(request).get('THEMES', [])
        for theme in themes:
            themes_data.append({
                'name': theme['name'],
                'slug': theme['slug'],
                'colors': theme['colors'],
                'description': f"Theme: {theme['name']}"
            })
        return success_response({'themes': themes_data})
    
    @action(detail=False, methods=['get'])
    def health(self, request):
        """Get comprehensive system health status."""
        health = get_system_health()
        status_code = 200 if health['overall_status'] == 'healthy' else 503
        if health['overall_status'] != 'healthy':
            logger.warning(f"Health check degraded/unhealthy: {health}")
        return Response({
            'status': 'success' if health['overall_status'] == 'healthy' else 'error',
            'message': f"System health: {health['overall_status']}",
            'data': health
        }, status=status_code)
    
    @action(detail=False, methods=['get'])
    def detailed_health(self, request):
        """Detailed health check for monitoring systems."""
        health_checker = SystemHealthChecker()
        results = health_checker.run_all_health_checks()
        
        # Determine overall status
        overall_status = 'healthy'
        if any(r['status'] == 'unhealthy' for r in results['checks']):
            overall_status = 'unhealthy'
        elif any(r['status'] == 'degraded' for r in results['checks']):
            overall_status = 'degraded'
        
        status_code = 200 if overall_status == 'healthy' else 503
        
        return Response({
            'status': overall_status,
            'timestamp': timezone.now().isoformat(),
            'checks': results['checks'],
            'summary': results['summary']
        }, status=status_code)
    
    @action(detail=False, methods=['get'])
    def quick_health(self, request):
        """Quick health check for load balancers."""
        status = get_quick_health_status()
        code = 200 if status == 'healthy' else 503
        if status != 'healthy':
            logger.warning(f"Quick health check failed: {status}")
        return Response({'status': status}, status=code)
    
    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get system performance summary."""
        summary = get_performance_summary(60)
        if summary['alerts']:
            logger.warning(f"Performance alerts: {summary['alerts']}")
        return Response({
            'status': 'success',
            'message': 'Performance summary',
            'data': summary
        })
    
    @action(detail=False, methods=['get'])
    def celery_health(self, request):
        """Get Celery system health status."""
        try:
            health_status = health_check_celery()
            return Response({
                'status': 'success',
                'message': f'Celery health check completed. Status: {health_status["overall_status"]}',
                'data': health_status
            })
        except Exception as e:
            logger.error(f"Error in Celery health check: {e}")
            return Response({
                'status': 'error',
                'message': f'Error performing Celery health check: {str(e)}',
                'data': {
                    'timestamp': timezone.now().isoformat(),
                    'overall_status': 'error',
                    'error': str(e)
                }
            }, status=500)


class TaskStatusViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing and monitoring background tasks.
    """
    serializer_class = TaskStatusSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter tasks by current user."""
        return TaskStatus.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    @extend_schema(parameters=[OpenApiParameter("pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="Task Status ID")])
    def status(self, request, pk=None):
        """Get detailed status of a specific task."""
        try:
            task_status = self.get_object()
            
            # Use the utility function to get comprehensive task status
            detailed_status = get_task_status(task_status.task_id)
            
            if detailed_status:
                return Response({
                    'status': 'success',
                    'message': 'Task status retrieved successfully',
                    'data': detailed_status
                })
            else:
                return Response({
                    'status': 'error',
                    'message': 'Task not found or status unavailable',
                    'data': {
                        'task_id': task_status.task_id,
                        'state': 'UNKNOWN',
                        'message': 'Task status could not be retrieved'
                    }
                }, status=404)
                
        except TaskStatus.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Task not found',
                'data': None
            }, status=404)
        except Exception as e:
            logger.error(f"Error retrieving task status: {e}")
            return Response({
                'status': 'error',
                'message': f'Error retrieving task status: {str(e)}',
                'data': None
            }, status=500)
    
    @action(detail=True, methods=['post'])
    @extend_schema(parameters=[OpenApiParameter("pk", OpenApiTypes.INT, OpenApiParameter.PATH, description="Task Status ID")])
    def cancel(self, request, pk=None):
        """Cancel a running task."""
        task_status = self.get_object()
        
        if task_status.is_completed:
            return Response({
                'error': 'Cannot cancel completed task'
            }, status=400)
        
        try:
            # Revoke task in Celery
            from celery import current_app
            current_app.control.revoke(task_status.task_id, terminate=True)
            
            # Update local status
            task_status.mark_cancelled()
            
            return Response({
                'message': 'Task cancelled successfully',
                'task_id': task_status.task_id
            })
            
        except Exception as e:
            return Response({
                'error': f'Error cancelling task: {str(e)}'
            }, status=500)


class BackgroundChartViewSet(viewsets.ViewSet):
    """
    ViewSet for background chart generation and processing.
    """
    permission_classes = [APIKeyOrJWTPermission]
    serializer_class = ChartGenerationSerializer  # Default serializer for documentation
    
    @action(detail=False, methods=['post'])
    def generate_chart(self, request):
        """Start background chart generation task."""
        try:
            # Validate input data
            data = request.data
            required_fields = ['date', 'time', 'latitude', 'longitude', 'timezone_str', 
                             'zodiac_type', 'house_system', 'model_name', 'temperature', 'max_tokens']
            
            for field in required_fields:
                if field not in data:
                    return Response({
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Convert to UTC
            from chart.views import local_to_utc
            utc_date, utc_time = local_to_utc(
                data['date'],
                data['time'],
                data['timezone_str']
            )
            
            # Prepare task parameters
            chart_params = {
                'utc_date': utc_date,
                'utc_time': utc_time,
                'latitude': float(data['latitude']),
                'longitude': float(data['longitude']),
                'zodiac_type': data['zodiac_type'],
                'house_system': data['house_system'],
                'model_name': data['model_name'],
                'temperature': float(data['temperature']),
                'max_tokens': int(data['max_tokens']),
                'location': data.get('location_name', 'Unknown')
            }
            
            # Use the new utility function for task creation with fallback
            task_result = create_task_with_fallback(
                task_func=generate_chart_task,
                args=[chart_params],
                user=request.user,
                task_type='chart_generation',
                parameters=chart_params
            )
            if not task_result:
                logger.error("create_task_with_fallback returned None")
                return Response({'error': 'Internal server error: task result is None'}, status=500)
            
            if task_result['success']:
                response_data = {
                    'task_id': task_result['task_id'],
                    'status': task_result['status'],
                    'message': task_result['message'],
                    'celery_available': task_result['celery_available'],
                    'status_url': f'/api/v1/tasks/{task_result["task_status_id"]}/status/'
                }
                
                # If task completed synchronously, include the result
                if task_result['status'] == 'SUCCESS' and 'result' in task_result:
                    response_data['result'] = task_result['result']
                    return Response(response_data, status=200)
                else:
                    return Response(response_data, status=202)
            else:
                return Response({
                    'error': task_result.get('error', 'Unknown error occurred'),
                    'message': task_result.get('message', 'No message')
                }, status=500)
            
        except Exception as e:
            logger.error(f"Error in generate_chart endpoint: {e}")
            return Response({
                'error': f'Error starting chart generation: {str(e)}'
            }, status=500)
    
    @action(detail=False, methods=['post'])
    def generate_interpretation(self, request):
        """Start background interpretation generation task."""
        try:
            # Validate input data
            data = request.data
            required_fields = ['chart_data', 'model_name', 'temperature', 'max_tokens']
            
            for field in required_fields:
                if field not in data:
                    return Response({
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            # Prepare task parameters
            interpretation_params = {
                'model_name': data['model_name'],
                'temperature': float(data['temperature']),
                'max_tokens': int(data['max_tokens']),
                'interpretation_type': data.get('interpretation_type', 'comprehensive')
            }
            
            # Use the new utility function for task creation with fallback
            task_result = create_task_with_fallback(
                task_func=generate_interpretation_task,
                args=[data['chart_data'], interpretation_params],
                user=request.user,
                task_type='interpretation',
                parameters=interpretation_params
            )
            if not task_result:
                logger.error("create_task_with_fallback returned None")
                return Response({'error': 'Internal server error: task result is None'}, status=500)
            
            if task_result['success']:
                response_data = {
                    'task_id': task_result['task_id'],
                    'status': task_result['status'],
                    'message': task_result['message'],
                    'celery_available': task_result['celery_available'],
                    'status_url': f'/api/v1/tasks/{task_result["task_status_id"]}/status/'
                }
                
                # If task completed synchronously, include the result
                if task_result['status'] == 'SUCCESS' and 'result' in task_result:
                    response_data['result'] = task_result['result']
                    return Response(response_data, status=200)
                else:
                    return Response(response_data, status=202)
            else:
                return Response({
                    'error': task_result.get('error', 'Unknown error occurred'),
                    'message': task_result.get('message', 'No message')
                }, status=500)
            
        except Exception as e:
            return Response({
                'error': f'Error starting interpretation generation: {str(e)}'
            }, status=500)
    
    @action(detail=False, methods=['post'])
    def calculate_ephemeris(self, request):
        """Start background ephemeris calculation task."""
        try:
            # Validate input data
            data = request.data
            required_fields = ['date', 'time', 'latitude', 'longitude', 'timezone_str', 
                             'zodiac_type', 'house_system']
            
            for field in required_fields:
                if field not in data:
                    return Response({
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            logger.info(f"Starting ephemeris calculation with data: {data}")
            
            # Convert to UTC
            from chart.views import local_to_utc
            utc_date, utc_time = local_to_utc(
                data['date'],
                data['time'],
                data['timezone_str']
            )
            
            logger.info(f"Converted to UTC: {utc_date}, {utc_time}")
            
            # Prepare task parameters
            ephemeris_params = {
                'utc_date': utc_date,
                'utc_time': utc_time,
                'latitude': float(data['latitude']),
                'longitude': float(data['longitude']),
                'zodiac_type': data['zodiac_type'],
                'house_system': data['house_system']
            }
            
            logger.info(f"Prepared ephemeris params: {ephemeris_params}")
            
            # Handle user for API key authentication
            user = request.user if hasattr(request, 'user') and request.user else None
            logger.info(f"User for task: {user}")
            
            # Use the new utility function for task creation with fallback
            logger.info("Calling create_task_with_fallback...")
            task_result = create_task_with_fallback(
                task_func=calculate_ephemeris_task,
                args=[ephemeris_params],
                user=user,
                task_type='ephemeris',
                parameters=ephemeris_params
            )
            
            logger.info(f"Task result: {task_result}")
            
            if task_result and task_result.get('success'):
                response_data = {
                    'task_id': task_result.get('task_id'),
                    'status': task_result.get('status'),
                    'message': task_result.get('message'),
                    'celery_available': task_result.get('celery_available'),
                    'status_url': f'/api/v1/tasks/{task_result.get("task_status_id")}/status/'
                }
                
                # If task completed synchronously, include the result
                if task_result.get('status') == 'SUCCESS' and 'result' in task_result:
                    response_data['result'] = task_result['result']
                    return Response(response_data, status=200)
                else:
                    return Response(response_data, status=202)
            else:
                error_msg = task_result.get('error', 'Unknown error occurred') if task_result else 'Task creation failed'
                logger.error(f"Task creation failed: {error_msg}")
                return Response({
                    'error': error_msg,
                    'message': task_result.get('message', 'Task creation failed') if task_result else 'Task creation failed'
                }, status=500)
            
        except Exception as e:
            logger.error(f"Error in calculate_ephemeris endpoint: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return Response({
                'error': f'Error starting ephemeris calculation: {str(e)}'
            }, status=500) 