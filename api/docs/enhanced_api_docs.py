"""
Enhanced API Documentation

This module provides comprehensive API documentation with:
- OpenAPI 3.0 specifications
- Security documentation
- Rate limiting information
- Error handling documentation
- Code examples
- Interactive documentation
"""

from drf_spectacular.extensions import OpenApiViewExtension
from drf_spectacular.plumbing import build_basic_type, build_parameter_type
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import JsonResponse
import json


class EnhancedAPIView(APIView):
    """Base API view with enhanced documentation and security"""
    
    def get_success_response(self, data, message="Success", status_code=200):
        """Standard success response format"""
        return Response({
            'success': True,
            'message': message,
            'data': data,
            'timestamp': self._get_timestamp()
        }, status=status_code)
    
    def get_error_response(self, error, message="Error", status_code=400):
        """Standard error response format"""
        return Response({
            'success': False,
            'error': error,
            'message': message,
            'timestamp': self._get_timestamp()
        }, status=status_code)
    
    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


# OpenAPI Documentation Extensions
class ChartGenerationViewExtension(OpenApiViewExtension):
    target_class = 'api.v1.views.ChartViewSet'
    
    def view_replacement(self):
        class Extended(self.target_class):
            @extend_schema(
                summary="Generate Astrological Chart",
                description="""
                Generate a comprehensive astrological birth chart with AI interpretation.
                
                This endpoint calculates planetary positions, houses, aspects, and dignities
                for a given birth date, time, and location. The calculation uses Swiss Ephemeris
                for accurate astronomical data and provides detailed astrological analysis.
                
                **Rate Limits:**
                - 10 chart generations per hour per IP
                - 1000 API requests per hour per IP
                
                **Security:**
                - Requires authentication (JWT token or API key)
                - Input validation and sanitization
                - Rate limiting protection
                """,
                tags=["charts"],
                examples=[
                    OpenApiExample(
                        "Basic Chart Generation",
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
                    ),
                    OpenApiExample(
                        "Minimal Chart Generation",
                        value={
                            "birth_date": "1985-08-20",
                            "birth_time": "10:15",
                            "latitude": 34.0522,
                            "longitude": -118.2437,
                            "timezone": "America/Los_Angeles",
                            "house_system": "whole_sign"
                        },
                        status_codes=["201"]
                    )
                ],
                responses={
                    201: OpenApiResponse(
                        description="Chart generated successfully",
                        examples=[
                            OpenApiExample(
                                "Success Response",
                                value={
                                    "success": True,
                                    "message": "Chart generated successfully",
                                    "data": {
                                        "chart_id": "uuid-string",
                                        "planets": {
                                            "Sun": {
                                                "sign": "Taurus",
                                                "degree_in_sign": 25.5,
                                                "house": 2,
                                                "retrograde": False,
                                                "dignity": "Exaltation"
                                            }
                                        },
                                        "houses": {
                                            "ascendant": {
                                                "sign": "Capricorn",
                                                "degree_in_sign": 15.2
                                            },
                                            "cusps": {
                                                1: {"sign": "Capricorn", "degree_in_sign": 15.2},
                                                2: {"sign": "Aquarius", "degree_in_sign": 5.8}
                                            }
                                        },
                                        "aspects": [
                                            {
                                                "planet1": "Sun",
                                                "planet2": "Moon",
                                                "type": "Trine",
                                                "orb": 2.3,
                                                "strength": "strong"
                                            }
                                        ],
                                        "interpretation": {
                                            "summary": "Your chart shows...",
                                            "planets": {
                                                "Sun": "With the Sun in Taurus..."
                                            }
                                        }
                                    }
                                }
                            )
                        ]
                    ),
                    400: OpenApiResponse(
                        description="Invalid input data",
                        examples=[
                            OpenApiExample(
                                "Validation Error",
                                value={
                                    "success": False,
                                    "error": "validation_error",
                                    "message": "Invalid birth date format",
                                    "details": {
                                        "birth_date": ["Date must be in YYYY-MM-DD format"]
                                    }
                                }
                            )
                        ]
                    ),
                    401: OpenApiResponse(
                        description="Authentication required",
                        examples=[
                            OpenApiExample(
                                "Authentication Error",
                                value={
                                    "success": False,
                                    "error": "authentication_required",
                                    "message": "Valid authentication credentials required"
                                }
                            )
                        ]
                    ),
                    429: OpenApiResponse(
                        description="Rate limit exceeded",
                        examples=[
                            OpenApiExample(
                                "Rate Limit Error",
                                value={
                                    "success": False,
                                    "error": "rate_limit_exceeded",
                                    "message": "Too many requests. Limit: 10 per hour"
                                }
                            )
                        ]
                    )
                }
            )
            def generate(self, request):
                return super().generate(request)
        
        return Extended


class AuthenticationViewExtension(OpenApiViewExtension):
    target_class = 'api.v1.views.AuthViewSet'
    
    def view_replacement(self):
        class Extended(self.target_class):
            @extend_schema(
                summary="User Registration",
                description="""
                Register a new user account and receive authentication tokens.
                
                **Security Features:**
                - Password strength validation
                - Email verification (optional)
                - Rate limiting: 5 attempts per 5 minutes
                - Input sanitization
                
                **Password Requirements:**
                - Minimum 8 characters
                - At least one uppercase letter
                - At least one lowercase letter
                - At least one number
                - At least one special character
                """,
                tags=["authentication"],
                examples=[
                    OpenApiExample(
                        "Successful Registration",
                        value={
                            "username": "johndoe",
                            "email": "john@example.com",
                            "password": "SecurePass123!",
                            "password_confirm": "SecurePass123!",
                            "first_name": "John",
                            "last_name": "Doe"
                        },
                        status_codes=["201"]
                    )
                ],
                responses={
                    201: OpenApiResponse(
                        description="User registered successfully",
                        examples=[
                            OpenApiExample(
                                "Success Response",
                                value={
                                    "success": True,
                                    "message": "User registered successfully",
                                    "data": {
                                        "user": {
                                            "id": 1,
                                            "username": "johndoe",
                                            "email": "john@example.com",
                                            "first_name": "John",
                                            "last_name": "Doe",
                                            "date_joined": "2024-01-15T10:30:00Z"
                                        },
                                        "tokens": {
                                            "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                                            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                                        }
                                    }
                                }
                            )
                        ]
                    ),
                    400: OpenApiResponse(
                        description="Registration failed",
                        examples=[
                            OpenApiExample(
                                "Validation Error",
                                value={
                                    "success": False,
                                    "error": "validation_error",
                                    "message": "Registration failed",
                                    "details": {
                                        "username": ["Username already exists"],
                                        "password": ["Password too weak"]
                                    }
                                }
                            )
                        ]
                    )
                }
            )
            def register(self, request):
                return super().register(request)
        
        return Extended


# API Documentation Views
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def api_documentation(request):
    """Main API documentation page"""
    return Response({
        'title': 'Outer Skies API Documentation',
        'version': '1.0.0',
        'description': 'Comprehensive astrological chart generation and interpretation API',
        'base_url': 'https://api.outer-skies.com/v1',
        'authentication': {
            'methods': ['JWT Token', 'API Key'],
            'jwt_header': 'Authorization: Bearer <token>',
            'api_key_header': 'X-API-Key: <your-api-key>'
        },
        'rate_limits': {
            'default': '100 requests per hour',
            'api': '1000 requests per hour',
            'chart_generation': '10 charts per hour',
            'authentication': '5 attempts per 5 minutes'
        },
        'endpoints': {
            'authentication': '/api/v1/auth/',
            'charts': '/api/v1/charts/',
            'users': '/api/v1/users/',
            'system': '/api/v1/system/'
        },
        'security': {
            'cors': 'Configured for allowed origins',
            'headers': 'Security headers enabled',
            'validation': 'Input validation and sanitization',
            'rate_limiting': 'IP-based rate limiting',
            'monitoring': 'Request logging and monitoring'
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def security_documentation(request):
    """Security documentation and guidelines"""
    return Response({
        'security_overview': {
            'authentication': {
                'jwt_tokens': {
                    'description': 'JSON Web Tokens for user authentication',
                    'expiration': 'Access tokens expire in 1 hour',
                    'refresh': 'Refresh tokens valid for 7 days',
                    'rotation': 'Automatic token rotation on refresh'
                },
                'api_keys': {
                    'description': 'API keys for service-to-service communication',
                    'format': '32-character hexadecimal string',
                    'permissions': 'Full API access',
                    'rotation': 'Manual rotation required'
                }
            },
            'rate_limiting': {
                'implementation': 'Redis-based rate limiting',
                'granularity': 'IP-based and user-based limits',
                'headers': 'Rate limit headers included in responses',
                'retry_after': 'Retry-After header for rate limit exceeded'
            },
            'input_validation': {
                'sanitization': 'Automatic input sanitization',
                'sql_injection': 'SQL injection protection',
                'xss_protection': 'Cross-site scripting protection',
                'file_uploads': 'File type and size validation'
            },
            'headers': {
                'security_headers': [
                    'X-Content-Type-Options: nosniff',
                    'X-Frame-Options: DENY',
                    'X-XSS-Protection: 1; mode=block',
                    'Strict-Transport-Security: max-age=31536000',
                    'Content-Security-Policy: default-src \'self\''
                ]
            }
        },
        'best_practices': [
            'Always use HTTPS in production',
            'Store API keys securely',
            'Implement proper error handling',
            'Monitor rate limits',
            'Validate all input data',
            'Use strong passwords',
            'Enable two-factor authentication',
            'Regular security audits'
        ],
        'error_handling': {
            '400': 'Bad Request - Invalid input data',
            '401': 'Unauthorized - Authentication required',
            '403': 'Forbidden - Access denied',
            '404': 'Not Found - Resource not found',
            '429': 'Too Many Requests - Rate limit exceeded',
            '500': 'Internal Server Error - Server error'
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def rate_limit_info(request):
    """Rate limiting information and current status"""
    from django.core.cache import cache
    
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    
    # Get current rate limit status
    rate_limits = {
        'default': cache.get(f"rate_limit:default:{client_ip}", 0),
        'api': cache.get(f"rate_limit:api:{client_ip}", 0),
        'chart_generation': cache.get(f"rate_limit:chart_generation:{client_ip}", 0),
        'auth': cache.get(f"rate_limit:auth:{client_ip}", 0)
    }
    
    limits = {
        'default': 100,
        'api': 1000,
        'chart_generation': 10,
        'auth': 5
    }
    
    return Response({
        'client_ip': client_ip,
        'rate_limits': {
            'default': {
                'current': rate_limits['default'],
                'limit': limits['default'],
                'remaining': limits['default'] - rate_limits['default'],
                'window': '1 hour'
            },
            'api': {
                'current': rate_limits['api'],
                'limit': limits['api'],
                'remaining': limits['api'] - rate_limits['api'],
                'window': '1 hour'
            },
            'chart_generation': {
                'current': rate_limits['chart_generation'],
                'limit': limits['chart_generation'],
                'remaining': limits['chart_generation'] - rate_limits['chart_generation'],
                'window': '1 hour'
            },
            'auth': {
                'current': rate_limits['auth'],
                'limit': limits['auth'],
                'remaining': limits['auth'] - rate_limits['auth'],
                'window': '5 minutes'
            }
        },
        'headers': {
            'X-RateLimit-Limit': 'Current limit for endpoint',
            'X-RateLimit-Remaining': 'Remaining requests',
            'X-RateLimit-Reset': 'Time when limit resets',
            'Retry-After': 'Seconds to wait when limit exceeded'
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_status(request):
    """API status and health information"""
    from monitoring.health_checks import get_system_health
    from monitoring.performance_monitor import get_performance_summary
    
    try:
        health = get_system_health()
        performance = get_performance_summary()
        
        return Response({
            'status': 'healthy',
            'timestamp': health.get('timestamp'),
            'services': {
                'database': health.get('database', {}).get('status', 'unknown'),
                'redis': health.get('redis', {}).get('status', 'unknown'),
                'celery': health.get('celery', {}).get('status', 'unknown'),
                'swiss_ephemeris': health.get('swiss_ephemeris', {}).get('status', 'unknown')
            },
            'performance': {
                'response_time_avg': performance.get('response_time_avg', 0),
                'requests_per_minute': performance.get('requests_per_minute', 0),
                'error_rate': performance.get('error_rate', 0)
            },
            'uptime': health.get('uptime', 0),
            'version': '1.0.0'
        })
    except Exception as e:
        return Response({
            'status': 'degraded',
            'error': str(e),
            'timestamp': time.time()
        }, status=500)


# Error Documentation
ERROR_CODES = {
    'validation_error': {
        'code': 400,
        'title': 'Validation Error',
        'description': 'The request data is invalid or missing required fields',
        'examples': [
            'Invalid date format',
            'Missing required field',
            'Value out of range'
        ]
    },
    'authentication_required': {
        'code': 401,
        'title': 'Authentication Required',
        'description': 'Valid authentication credentials are required',
        'examples': [
            'Missing JWT token',
            'Invalid API key',
            'Expired token'
        ]
    },
    'permission_denied': {
        'code': 403,
        'title': 'Permission Denied',
        'description': 'You do not have permission to access this resource',
        'examples': [
            'Insufficient permissions',
            'Account suspended',
            'IP blocked'
        ]
    },
    'not_found': {
        'code': 404,
        'title': 'Not Found',
        'description': 'The requested resource was not found',
        'examples': [
            'Chart not found',
            'User not found',
            'Invalid endpoint'
        ]
    },
    'rate_limit_exceeded': {
        'code': 429,
        'title': 'Rate Limit Exceeded',
        'description': 'Too many requests in the specified time period',
        'examples': [
            'Too many chart generations',
            'Too many API requests',
            'Too many authentication attempts'
        ]
    },
    'internal_server_error': {
        'code': 500,
        'title': 'Internal Server Error',
        'description': 'An unexpected error occurred on the server',
        'examples': [
            'Database connection error',
            'External service unavailable',
            'Configuration error'
        ]
    }
}


@api_view(['GET'])
@permission_classes([AllowAny])
def error_codes(request):
    """Error codes and their meanings"""
    return Response({
        'error_codes': ERROR_CODES,
        'standard_response_format': {
            'success': False,
            'error': 'error_code',
            'message': 'Human-readable error message',
            'details': 'Additional error details (optional)',
            'timestamp': 'ISO 8601 timestamp'
        },
        'handling_errors': [
            'Always check the success field first',
            'Use the error code for programmatic handling',
            'Display the message to users',
            'Log details for debugging',
            'Implement exponential backoff for rate limits'
        ]
    })


# Code Examples
@api_view(['GET'])
@permission_classes([AllowAny])
def code_examples(request):
    """Code examples for common API operations"""
    return Response({
        'javascript': {
            'chart_generation': '''
// Generate a birth chart
const response = await fetch('/api/v1/charts/generate/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({
        birth_date: '1990-05-15',
        birth_time: '14:30',
        latitude: 40.7128,
        longitude: -74.0060,
        timezone: 'America/New_York',
        house_system: 'placidus'
    })
});

const chart = await response.json();
console.log(chart.data.planets);
            ''',
            'authentication': '''
// Register a new user
const response = await fetch('/api/v1/auth/register/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        username: 'johndoe',
        email: 'john@example.com',
        password: 'SecurePass123!',
        password_confirm: 'SecurePass123!'
    })
});

const result = await response.json();
localStorage.setItem('access_token', result.data.tokens.access);
            '''
        },
        'python': {
            'chart_generation': '''
import requests

# Generate a birth chart
response = requests.post(
    'https://api.outer-skies.com/v1/charts/generate/',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    json={
        'birth_date': '1990-05-15',
        'birth_time': '14:30',
        'latitude': 40.7128,
        'longitude': -74.0060,
        'timezone': 'America/New_York',
        'house_system': 'placidus'
    }
)

chart = response.json()
print(chart['data']['planets'])
            ''',
            'error_handling': '''
import requests
import time

def make_api_request(url, data, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=data)
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
                continue
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
            '''
        },
        'curl': {
            'chart_generation': '''
# Generate a birth chart
curl -X POST https://api.outer-skies.com/v1/charts/generate/ \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "birth_date": "1990-05-15",
    "birth_time": "14:30",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timezone": "America/New_York",
    "house_system": "placidus"
  }'
            ''',
            'authentication': '''
# Register a new user
curl -X POST https://api.outer-skies.com/v1/auth/register/ \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "password_confirm": "SecurePass123!"
  }'
            '''
        }
    }) 