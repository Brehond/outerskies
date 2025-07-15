"""
Security Headers Middleware

Focused middleware for adding security headers and CORS configuration.
"""

import logging
from django.http import HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security_audit')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Focused middleware for adding comprehensive security headers and CORS.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        
        # CORS configuration
        self.cors_allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        self.cors_allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        self.cors_allowed_headers = [
            'Content-Type', 'Authorization', 'X-Requested-With',
            'Accept', 'Origin', 'X-API-Key', 'X-Signature',
            'X-Timestamp', 'X-Nonce'
        ]
    
    def process_response(self, request, response):
        """Add security headers and CORS headers."""
        # Add comprehensive security headers
        self._add_security_headers(response)
        
        # Add CORS headers if needed
        self._add_cors_headers(request, response)
        
        return response
    
    def _add_security_headers(self, response):
        """Add comprehensive security headers."""
        # Content Security Policy
        response['Content-Security-Policy'] = self._get_csp_header()
        
        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Content Type Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Frame Options
        response['X-Frame-Options'] = 'DENY'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cross-Origin Opener Policy
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cross-Origin Embedder Policy
        response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        # Permissions Policy
        response['Permissions-Policy'] = self._get_permissions_policy()
        
        # HSTS (only for HTTPS)
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    
    def _get_csp_header(self):
        """Get Content Security Policy header."""
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.openrouter.ai https://api.stripe.com",
            "frame-src 'self' https://js.stripe.com https://hooks.stripe.com",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ]
        return '; '.join(csp_directives)
    
    def _get_permissions_policy(self):
        """Get Permissions Policy header."""
        policies = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()"
        ]
        return ', '.join(policies)
    
    def _add_cors_headers(self, request, response):
        """Add CORS headers if needed."""
        origin = request.META.get('HTTP_ORIGIN')
        
        if not origin:
            return
        
        # Check if origin is allowed
        if origin in self.cors_allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            
            # Handle preflight requests
            if request.method == 'OPTIONS':
                response['Access-Control-Allow-Methods'] = ', '.join(self.cors_allowed_methods)
                response['Access-Control-Allow-Headers'] = ', '.join(self.cors_allowed_headers)
                response['Access-Control-Max-Age'] = '86400'  # 24 hours
        else:
            # Log unauthorized CORS attempt
            logger.warning(f'Unauthorized CORS request from origin: {origin}')
            response['Access-Control-Allow-Origin'] = 'null' 