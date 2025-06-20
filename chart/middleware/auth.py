from django.http import HttpResponse, JsonResponse
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging
import jwt
from datetime import datetime
from django.core.cache import cache
from functools import wraps
import time
import hmac
import hashlib
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger('security')

class APIAuthMiddleware:
    """
    API Authentication middleware that handles:
    - JWT token validation
    - API key authentication
    - Path-based access control
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.jwt_secret = getattr(settings, 'JWT_SECRET_KEY', 'your-secret-key')
        self.jwt_algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')
        self.api_key_header = getattr(settings, 'API_KEY_HEADER', 'X-API-Key')
        
        # Define path-based access control
        self.public_paths = {
            '/api/chart/public/',
            '/api/data/public/',
            '/api/health/'
        }
        
        self.admin_paths = {
            '/api/admin/',
            '/api/settings/'
        }
        
        self.jwt_auth = JWTAuthentication()
        
    def __call__(self, request):
        # Skip authentication for static/media files and test requests
        if request.path.startswith(('/static/', '/media/')) or settings.DEBUG:
            return self.get_response(request)
            
        # Check API key
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != settings.API_KEY:
            logger.warning(f"Invalid API key: {api_key}")
            return HttpResponse('Invalid API key', status=400)
            
        # Check request signature
        if not self._verify_signature(request):
            logger.warning("Invalid request signature")
            return HttpResponse('Invalid signature', status=400)
            
        # Check JWT token
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                validated_token = self.jwt_auth.get_validated_token(token)
                request.user = self.jwt_auth.get_user(validated_token)
        except (InvalidToken, TokenError) as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return HttpResponse('Invalid token', status=400)
            
        # Check path-based access control
        if not self._check_path_access(request):
            return JsonResponse({'error': 'Access denied'}, status=403)
            
        return self.get_response(request)
        
    def _validate_jwt(self, token):
        """Validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            
            # Check if token is blacklisted
            if cache.get(f'blacklisted_token_{token}'):
                return False
                
            # Add user info to request
            request.user = payload.get('user')
            request.roles = payload.get('roles', [])
            return True
            
        except jwt.ExpiredSignatureError:
            logger.warning('Expired JWT token')
            return False
        except jwt.InvalidTokenError:
            logger.warning('Invalid JWT token')
            return False
            
    def _validate_api_key(self, api_key):
        """Validate API key."""
        # Check if API key exists and is active
        if not cache.get(f'api_key_{api_key}'):
            return False
            
        # Add API key info to request
        request.api_key = api_key
        return True
        
    def _check_path_access(self, request):
        """Check if user has access to the requested path."""
        # Admin paths require admin role
        if request.path in self.admin_paths:
            return 'admin' in getattr(request, 'roles', [])
            
        return True
        
    def blacklist_token(self, token):
        """Add a token to the blacklist."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            exp = payload.get('exp', 0)
            ttl = exp - int(time.time())
            if ttl > 0:
                cache.set(f'blacklisted_token_{token}', True, ttl)
                return True
        except:
            pass
        return False
        
    def require_auth(self, view_func):
        """Decorator to require authentication for a view."""
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not hasattr(request, 'user') and not hasattr(request, 'api_key'):
                return JsonResponse({'error': 'Authentication required'}, status=401)
            return view_func(request, *args, **kwargs)
        return wrapped_view
        
    def require_role(self, role):
        """Decorator to require a specific role for a view."""
        def decorator(view_func):
            @wraps(view_func)
            def wrapped_view(request, *args, **kwargs):
                if not hasattr(request, 'roles') or role not in request.roles:
                    return JsonResponse({'error': 'Insufficient permissions'}, status=403)
                return view_func(request, *args, **kwargs)
            return wrapped_view
        return decorator
        
    def _verify_signature(self, request):
        """Verify request signature."""
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp')
        nonce = request.headers.get('X-Nonce')
        
        if not all([signature, timestamp, nonce]):
            return False
            
        # Check timestamp (within 5 minutes)
        try:
            timestamp = int(timestamp)
            if abs(time.time() - timestamp) > 300:
                return False
        except ValueError:
            return False
            
        # Generate expected signature
        method = request.method
        path = request.path
        query_string = request.META.get('QUERY_STRING', '')
        
        # Handle binary data by base64 encoding
        if request.body:
            import base64
            body = base64.b64encode(request.body).decode('utf-8')
        else:
            body = ''
        
        expected_signature = self._generate_signature(method, path, query_string, timestamp, nonce, body)
        return hmac.compare_digest(signature, expected_signature)
        
    def _generate_signature(self, method, path, query_string, timestamp, nonce, body=''):
        """Generate request signature."""
        signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
        return hmac.new(
            settings.API_SECRET.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest() 