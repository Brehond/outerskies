import logging
from django.conf import settings

logger = logging.getLogger('security')

class CORSMiddleware:
    """
    CORS middleware that handles:
    - Cross-origin request validation
    - CORS headers
    - Preflight requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', ['*'])
        self.allowed_methods = getattr(settings, 'CORS_ALLOWED_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
        self.allowed_headers = getattr(settings, 'CORS_ALLOWED_HEADERS', [
            'Content-Type',
            'Authorization',
            'X-API-Key',
            'X-Requested-With'
        ])
        self.exposed_headers = getattr(settings, 'CORS_EXPOSED_HEADERS', [
            'Content-Type',
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset'
        ])
        self.max_age = getattr(settings, 'CORS_MAX_AGE', 86400)  # 24 hours
        self.allow_credentials = getattr(settings, 'CORS_ALLOW_CREDENTIALS', True)
        
    def __call__(self, request):
        # Handle preflight requests
        if request.method == 'OPTIONS':
            return self._handle_preflight(request)
            
        # Process the request
        response = self.get_response(request)
        
        # Add CORS headers to response
        return self._add_cors_headers(request, response)
        
    def _handle_preflight(self, request):
        """Handle OPTIONS preflight requests."""
        response = HttpResponse()
        
        # Check origin
        origin = request.headers.get('Origin')
        if not self._is_origin_allowed(origin):
            return HttpResponse(status=403)
            
        # Check requested method
        requested_method = request.headers.get('Access-Control-Request-Method')
        if requested_method and requested_method not in self.allowed_methods:
            return HttpResponse(status=403)
            
        # Check requested headers
        requested_headers = request.headers.get('Access-Control-Request-Headers', '').split(',')
        if not all(header.strip() in self.allowed_headers for header in requested_headers):
            return HttpResponse(status=403)
            
        # Add CORS headers
        response = self._add_cors_headers(request, response)
        
        # Add preflight-specific headers
        response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
        response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
        response['Access-Control-Max-Age'] = str(self.max_age)
        
        return response
        
    def _add_cors_headers(self, request, response):
        """Add CORS headers to the response."""
        origin = request.headers.get('Origin')
        
        if self._is_origin_allowed(origin):
            response['Access-Control-Allow-Origin'] = origin if self.allow_credentials else '*'
            response['Access-Control-Allow-Credentials'] = str(self.allow_credentials).lower()
            response['Access-Control-Expose-Headers'] = ', '.join(self.exposed_headers)
            
        return response
        
    def _is_origin_allowed(self, origin):
        """Check if the origin is allowed."""
        if not origin:
            return False
        if '*' in self.allowed_origins:
            return True
        return origin in self.allowed_origins 