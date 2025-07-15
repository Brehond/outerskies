"""
Input Validation Middleware

Focused middleware for validating and sanitizing request input data.
"""

import re
import json
import logging
from typing import Any, Optional
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('security_audit')


class InputValidationMiddleware(MiddlewareMixin):
    """
    Focused input validation middleware for request sanitization and validation.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        
        # Request size limits
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        
        # Security patterns for XSS detection
        self.xss_patterns = [
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'onload\s*=', re.IGNORECASE),
            re.compile(r'onerror\s*=', re.IGNORECASE),
            re.compile(r'<iframe[^>]*>', re.IGNORECASE),
            re.compile(r'<object[^>]*>', re.IGNORECASE),
            re.compile(r'<embed[^>]*>', re.IGNORECASE),
        ]
        
        # SQL injection patterns
        self.sql_patterns = [
            re.compile(r"(\%27)|(\')|(\-\-)|(\%23)|(#)", re.IGNORECASE),
            re.compile(r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))union", re.IGNORECASE),
            re.compile(r"exec(\s|\+)+(s|x)p\w+", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))((\%61)|a|(\%41))((\%6E)|n|(\%4E))((\%64)|d|(\%44))", re.IGNORECASE),
        ]
        
        # Safe content types for caching
        self.safe_cache_content_types = [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data'
        ]
        
        # Maximum cache size
        self.max_cache_size = 1024 * 1024  # 1MB
    
    def process_request(self, request):
        """Validate and sanitize request input."""
        # Skip for static files and health checks
        if self._should_skip_validation(request):
            return None
        
        # 1. Check request size
        if self._check_request_size(request):
            logger.warning(f'Request too large from {self._get_client_ip(request)}')
            return JsonResponse({
                'error': 'Request too large',
                'message': f'Request size exceeds {self.max_request_size} bytes'
            }, status=413)
        
        # 2. Cache request body for safe content types
        if self._should_cache_body(request):
            self._cache_request_body(request)
        
        # 3. Validate request data
        validation_result = self._validate_request_data(request)
        if validation_result:
            return validation_result
        
        # 4. Check for security threats
        threat_result = self._check_security_threats(request)
        if threat_result:
            return threat_result
        
        return None
    
    def _should_skip_validation(self, request) -> bool:
        """Determine if validation should be skipped."""
        skip_paths = [
            '/static/', '/media/', '/favicon.ico',
            '/api/v1/system/health/', '/api/v1/system/quick-health/'
        ]
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _check_request_size(self, request) -> bool:
        """Check if request size exceeds limits."""
        content_length = request.META.get('CONTENT_LENGTH', 0)
        return content_length and int(content_length) > self.max_request_size
    
    def _should_cache_body(self, request) -> bool:
        """Determine if request body should be cached."""
        content_type = request.content_type or ''
        content_length = request.META.get('CONTENT_LENGTH', 0)
        
        return (
            any(safe_type in content_type for safe_type in self.safe_cache_content_types) and
            content_length and int(content_length) < self.max_cache_size
        )
    
    def _cache_request_body(self, request):
        """Cache request body for later access."""
        try:
            if hasattr(request, '_body'):
                # Body already read, store it
                request._cached_body = request._body
            elif request.content_type == 'application/json':
                # Read and parse JSON body
                body = request.body.decode('utf-8')
                request._cached_body = json.loads(body)
            else:
                # Read raw body
                request._cached_body = request.body
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            logger.warning(f'Failed to cache request body: {e}')
            request._cached_body = None
    
    def _validate_request_data(self, request) -> Optional[HttpResponse]:
        """Validate request data for common issues."""
        # Check for suspicious user agents
        if self._is_suspicious_user_agent(request):
            logger.warning(f'Suspicious user agent from {self._get_client_ip(request)}')
            return JsonResponse({
                'error': 'Invalid request',
                'message': 'Suspicious user agent detected'
            }, status=400)
        
        # Check for excessive frequency (basic check)
        if self._is_excessive_frequency(request):
            logger.warning(f'Excessive request frequency from {self._get_client_ip(request)}')
            return JsonResponse({
                'error': 'Too many requests',
                'message': 'Request frequency too high'
            }, status=429)
        
        return None
    
    def _check_security_threats(self, request) -> Optional[HttpResponse]:
        """Check for security threats in request data."""
        # Check for SQL injection patterns
        if self._has_sql_injection_patterns(request):
            logger.warning(f'SQL injection attempt from {self._get_client_ip(request)}')
            return JsonResponse({
                'error': 'Invalid request',
                'message': 'Malicious input detected'
            }, status=400)
        
        # Check for XSS patterns
        if self._has_xss_patterns(request):
            logger.warning(f'XSS attempt from {self._get_client_ip(request)}')
            return JsonResponse({
                'error': 'Invalid request',
                'message': 'Malicious input detected'
            }, status=400)
        
        return None
    
    def _is_suspicious_user_agent(self, request) -> bool:
        """Check for suspicious user agents."""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper',
            'curl', 'wget', 'python-requests',
            'sqlmap', 'nikto', 'nmap'
        ]
        
        return any(pattern in user_agent for pattern in suspicious_patterns)
    
    def _is_excessive_frequency(self, request) -> bool:
        """Basic frequency check (rate limiting handles the main logic)."""
        # This is a basic check - rate limiting middleware handles the main logic
        return False
    
    def _has_sql_injection_patterns(self, request) -> bool:
        """Check for SQL injection patterns in request data."""
        # Check URL parameters
        for key, value in request.GET.items():
            if self._contains_sql_patterns(str(value)):
                return True
        
        # Check POST data
        for key, value in request.POST.items():
            if self._contains_sql_patterns(str(value)):
                return True
        
        # Check JSON body if available
        if hasattr(request, '_cached_body') and isinstance(request._cached_body, dict):
            return self._check_dict_for_sql_patterns(request._cached_body)
        
        return False
    
    def _has_xss_patterns(self, request) -> bool:
        """Check for XSS patterns in request data."""
        # Check URL parameters
        for key, value in request.GET.items():
            if self._contains_xss_patterns(str(value)):
                return True
        
        # Check POST data
        for key, value in request.POST.items():
            if self._contains_xss_patterns(str(value)):
                return True
        
        # Check JSON body if available
        if hasattr(request, '_cached_body') and isinstance(request._cached_body, dict):
            return self._check_dict_for_xss_patterns(request._cached_body)
        
        return False
    
    def _contains_sql_patterns(self, content: str) -> bool:
        """Check if content contains SQL injection patterns."""
        return any(pattern.search(content) for pattern in self.sql_patterns)
    
    def _contains_xss_patterns(self, content: str) -> bool:
        """Check if content contains XSS patterns."""
        return any(pattern.search(content) for pattern in self.xss_patterns)
    
    def _check_dict_for_sql_patterns(self, data: dict) -> bool:
        """Recursively check dictionary for SQL patterns."""
        for key, value in data.items():
            if isinstance(value, dict):
                if self._check_dict_for_sql_patterns(value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if self._check_dict_for_sql_patterns(item):
                            return True
                    elif isinstance(item, str) and self._contains_sql_patterns(item):
                        return True
            elif isinstance(value, str) and self._contains_sql_patterns(value):
                return True
        return False
    
    def _check_dict_for_xss_patterns(self, data: dict) -> bool:
        """Recursively check dictionary for XSS patterns."""
        for key, value in data.items():
            if isinstance(value, dict):
                if self._check_dict_for_xss_patterns(value):
                    return True
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if self._check_dict_for_xss_patterns(item):
                            return True
                    elif isinstance(item, str) and self._contains_xss_patterns(item):
                        return True
            elif isinstance(value, str) and self._contains_xss_patterns(value):
                return True
        return False
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1') 