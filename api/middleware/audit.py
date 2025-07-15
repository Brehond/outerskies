"""
Audit Middleware

Focused middleware for request/response logging and security auditing.
"""

import time
import json
import logging
from typing import Dict, Any
from django.http import HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security_audit')


class AuditMiddleware(MiddlewareMixin):
    """
    Focused middleware for comprehensive request/response auditing and security logging.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.audit_enabled = getattr(settings, 'AUDIT_ENABLED', True)
    
    def process_request(self, request):
        """Log request for audit."""
        if not self.audit_enabled:
            return None
        
        # Add request start time
        request.start_time = time.time()
        
        # Skip audit for static files and health checks
        if self._should_skip_audit(request):
            return None
        
        # Log request details
        self._log_request_audit(request)
        
        return None
    
    def process_response(self, request, response):
        """Log response for audit."""
        if not self.audit_enabled or not hasattr(request, 'start_time'):
            return response
        
        # Skip audit for static files and health checks
        if self._should_skip_audit(request):
            return response
        
        # Calculate duration
        duration = time.time() - request.start_time
        
        # Log response details
        self._log_response_audit(request, response, duration)
        
        return response
    
    def process_exception(self, request, exception):
        """Log exceptions for audit."""
        if not self.audit_enabled:
            return None
        
        # Don't handle DRF exceptions - let DRF handle them
        from rest_framework.exceptions import APIException
        if isinstance(exception, APIException):
            return None
        
        # Calculate duration if available
        duration = None
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
        
        # Log exception details
        self._log_exception_audit(request, exception, duration)
        
        return None
    
    def _should_skip_audit(self, request) -> bool:
        """Determine if audit should be skipped."""
        skip_paths = [
            '/static/', '/media/', '/favicon.ico',
            '/api/v1/system/health/', '/api/v1/system/quick-health/'
        ]
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _log_request_audit(self, request):
        """Log request details for audit."""
        client_ip = self._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        audit_data = {
            'timestamp': time.time(),
            'type': 'request',
            'method': request.method,
            'path': request.path,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'content_type': request.content_type,
            'content_length': request.META.get('CONTENT_LENGTH', 0),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
            'session_id': request.session.session_key if hasattr(request, 'session') else None,
        }
        
        # Add query parameters (sanitized)
        if request.GET:
            audit_data['query_params'] = dict(request.GET)
        
        # Add headers (sanitized)
        sensitive_headers = ['authorization', 'cookie', 'x-api-key', 'x-signature']
        headers = {}
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].lower()
                if header_name not in sensitive_headers:
                    headers[header_name] = value
        audit_data['headers'] = headers
        
        logger.info(f"Request audit: {json.dumps(audit_data)}")
    
    def _log_response_audit(self, request, response, duration: float):
        """Log response details for audit."""
        client_ip = self._get_client_ip(request)
        
        audit_data = {
            'timestamp': time.time(),
            'type': 'response',
            'method': request.method,
            'path': request.path,
            'client_ip': client_ip,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
        }
        
        # Log security-relevant responses
        if response.status_code in [401, 403, 429, 500]:
            logger.warning(f"Security response audit: {json.dumps(audit_data)}")
        else:
            logger.info(f"Response audit: {json.dumps(audit_data)}")
    
    def _log_exception_audit(self, request, exception, duration: float):
        """Log exception details for audit."""
        client_ip = self._get_client_ip(request)
        
        audit_data = {
            'timestamp': time.time(),
            'type': 'exception',
            'method': request.method,
            'path': request.path,
            'client_ip': client_ip,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'duration_ms': round(duration * 1000, 2) if duration else None,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
        }
        
        logger.error(f"Exception audit: {json.dumps(audit_data)}")
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1') 