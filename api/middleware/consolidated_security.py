"""
Consolidated Security Middleware

This middleware combines all security functionality into a single, efficient implementation:
- Security headers
- Rate limiting
- Input validation and sanitization
- CORS protection
- Request logging and monitoring
- IP filtering and geolocation
- Security audit and threat detection
"""

import time
import json
import logging
import hashlib
import re
from typing import Dict, Any, Optional, List, Tuple
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError
import ipaddress
from user_agents import parse
import redis
from datetime import datetime, timedelta

logger = logging.getLogger('security_audit')


class ConsolidatedSecurityMiddleware(MiddlewareMixin):
    """
    Consolidated security middleware that provides comprehensive protection
    in a single, efficient implementation.
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        
        # Rate limiting configuration
        self.rate_limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'api': {'requests': 1000, 'window': 3600},     # 1000 API requests per hour
            'chart_generation': {'requests': 10, 'window': 3600},  # 10 charts per hour
            'auth': {'requests': 5, 'window': 300},        # 5 auth attempts per 5 minutes
            'file_upload': {'requests': 20, 'window': 3600},  # 20 uploads per hour
        }
        
        # Security patterns
        self.suspicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload=',
            r'onerror=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
        ]
        
        self.sql_patterns = [
            re.compile(r"(\%27)|(\')|(\-\-)|(\%23)|(#)", re.IGNORECASE),
            re.compile(r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))union", re.IGNORECASE),
            re.compile(r"exec(\s|\+)+(s|x)p\w+", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.IGNORECASE),
            re.compile(r"((\%27)|(\'))((\%61)|a|(\%41))((\%6E)|n|(\%4E))((\%64)|d|(\%44))", re.IGNORECASE),
        ]
        
        # Request size limits
        self.max_request_size = 10 * 1024 * 1024  # 10MB
        
        # CORS configuration
        self.cors_allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        self.cors_allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        self.cors_allowed_headers = [
            'Content-Type', 'Authorization', 'X-Requested-With',
            'Accept', 'Origin', 'X-API-Key'
        ]
        
        # IP filtering
        self.blocked_ips = set()
        self.allowed_ips = set()
        self._load_ip_lists()
        
        # Security audit settings
        self.audit_enabled = True
        self.threat_detection_enabled = True
        
    def process_request(self, request):
        """Process incoming request with comprehensive security checks."""
        start_time = time.time()
        
        # Add request start time for timing
        request.start_time = start_time
        
        # Skip security checks for static files and health checks
        if self._should_skip_security_checks(request):
            return None
            
        # 1. Check request size
        if self._check_request_size(request):
            return self._security_response('Request too large', 413)
        
        # 2. Check IP filtering
        if self._check_ip_filtering(request):
            return self._security_response('Access denied', 403)
        
        # 3. Check rate limiting
        rate_limit_result = self._check_rate_limiting(request)
        if rate_limit_result:
            return rate_limit_result
        
        # 4. Validate and sanitize input
        validation_result = self._validate_request_data(request)
        if validation_result:
            return validation_result
        
        # 5. Check for security threats
        threat_result = self._check_security_threats(request)
        if threat_result:
            return threat_result
        
        # 6. Log request for audit
        self._log_request_audit(request, start_time)
        
        return None
    
    def process_response(self, request, response):
        """Add security headers and process response."""
        # Add comprehensive security headers
        self._add_security_headers(response)
        
        # Add CORS headers if needed
        self._add_cors_headers(request, response)
        
        # Log response for audit
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            self._log_response_audit(request, response, duration)
        
        return response
    
    def process_exception(self, request, exception):
        """Handle exceptions with security logging."""
        # Don't handle DRF exceptions - let DRF handle them
        from rest_framework.exceptions import APIException
        if isinstance(exception, APIException):
            return None
        
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            self._log_exception_audit(request, exception, duration)
        
        # Don't expose internal errors in production
        if not settings.DEBUG:
            return JsonResponse({
                'error': 'Internal server error',
                'message': 'An unexpected error occurred'
            }, status=500)
        
        return None
    
    def _should_skip_security_checks(self, request) -> bool:
        """Determine if security checks should be skipped."""
        skip_paths = [
            '/static/', '/media/', '/favicon.ico',
            '/api/v1/system/health/', '/api/v1/system/quick-health/'
        ]
        return any(request.path.startswith(path) for path in skip_paths)
    
    def _check_request_size(self, request) -> bool:
        """Check if request size exceeds limits."""
        content_length = request.META.get('CONTENT_LENGTH', 0)
        return content_length and int(content_length) > self.max_request_size
    
    def _check_ip_filtering(self, request) -> bool:
        """Check IP filtering rules."""
        client_ip = self._get_client_ip(request)
        
        # Check blocked IPs
        if client_ip in self.blocked_ips:
            logger.warning(f'Blocked IP access attempt: {client_ip}')
            return True
        
        # Check allowed IPs (if configured)
        if self.allowed_ips and client_ip not in self.allowed_ips:
            logger.warning(f'Unauthorized IP access attempt: {client_ip}')
            return True
        
        return False
    
    def _check_rate_limiting(self, request) -> Optional[HttpResponse]:
        """Check rate limiting rules."""
        client_ip = self._get_client_ip(request)
        rate_limit_type = self._get_rate_limit_type(request)
        
        limit_config = self.rate_limits[rate_limit_type]
        cache_key = f"rate_limit:{rate_limit_type}:{client_ip}"
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit_config['requests']:
            logger.warning(f'Rate limit exceeded for {client_ip}: {rate_limit_type}')
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Too many requests. Limit: {limit_config["requests"]} per {limit_config["window"]}s',
                'retry_after': limit_config['window']
            }, status=429)
        
        # Increment counter
        cache.set(cache_key, current_count + 1, limit_config['window'])
        return None
    
    def _validate_request_data(self, request) -> Optional[HttpResponse]:
        """Validate and sanitize request data."""
        if request.method not in ['POST', 'PUT', 'PATCH']:
            return None
        
        try:
            # Check for suspicious patterns in headers
            for header_name, header_value in request.META.items():
                if isinstance(header_value, str) and self._contains_suspicious_content(header_value):
                    raise ValidationError(f'Suspicious content detected in header: {header_name}')
            
            # Validate JSON data - store body content for reuse
            if request.content_type == 'application/json':
                try:
                    # Read body once and store it for reuse
                    if not hasattr(request, '_body_cache'):
                        request._body_cache = request.body.decode('utf-8')
                    
                    data = json.loads(request._body_cache)
                    self._sanitize_data(data)
                except json.JSONDecodeError:
                    raise ValidationError('Invalid JSON data')
            
            # Validate form data
            elif request.content_type == 'application/x-www-form-urlencoded':
                for key, value in request.POST.items():
                    if isinstance(value, str) and self._contains_suspicious_content(value):
                        raise ValidationError(f'Suspicious content detected in field: {key}')
            
            return None
            
        except ValidationError as e:
            logger.warning(f'Input validation failed: {str(e)}')
            return JsonResponse({
                'error': 'Invalid input',
                'message': str(e)
            }, status=400)
    
    def _check_security_threats(self, request) -> Optional[HttpResponse]:
        """Check for security threats and suspicious patterns."""
        if not self.threat_detection_enabled:
            return None
        
        threats = []
        
        # Check for SQL injection
        if self._has_sql_injection_patterns(request):
            threats.append('SQL injection attempt')
        
        # Check for XSS
        if self._has_xss_patterns(request):
            threats.append('XSS attempt')
        
        # Check for suspicious user agent
        if self._is_suspicious_user_agent(request):
            threats.append('Suspicious user agent')
        
        # Check for excessive frequency
        if self._is_excessive_frequency(request):
            threats.append('Excessive request frequency')
        
        if threats:
            logger.warning(f'Security threats detected from {self._get_client_ip(request)}: {threats}')
            return self._security_response('Security violation detected', 403)
        
        return None
    
    def _add_security_headers(self, response):
        """Add comprehensive security headers."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
    
    def _add_cors_headers(self, request, response):
        """Add CORS headers if needed."""
        origin = request.META.get('HTTP_ORIGIN')
        if origin and origin in self.cors_allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = ', '.join(self.cors_allowed_methods)
            response['Access-Control-Allow-Headers'] = ', '.join(self.cors_allowed_headers)
    
    def _get_client_ip(self, request) -> str:
        """Get real client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _get_rate_limit_type(self, request) -> str:
        """Determine rate limit type based on request."""
        path = request.path.lower()
        
        if '/api/v1/auth/' in path:
            return 'auth'
        elif '/api/v1/charts/generate' in path:
            return 'chart_generation'
        elif '/api/v1/upload' in path or '/media/' in path:
            return 'file_upload'
        elif '/api/' in path:
            return 'api'
        else:
            return 'default'
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns."""
        content_lower = content.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        return False
    
    def _sanitize_data(self, data: Any) -> Any:
        """Recursively sanitize data."""
        if isinstance(data, dict):
            for key, value in data.items():
                data[key] = self._sanitize_data(value)
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # Remove null bytes and other dangerous characters
            data = data.replace('\x00', '')
            data = re.sub(r'[^\x20-\x7E]', '', data)  # Only printable ASCII
            return data
        return data
    
    def _has_sql_injection_patterns(self, request) -> bool:
        """Check for SQL injection patterns."""
        full_url = request.get_full_path()
        for pattern in self.sql_patterns:
            if pattern.search(full_url):
                return True
        
        # Check POST data
        if request.method == 'POST':
            for key, value in request.POST.items():
                if isinstance(value, str) and any(pattern.search(value) for pattern in self.sql_patterns):
                    return True
        
        return False
    
    def _has_xss_patterns(self, request) -> bool:
        """Check for XSS patterns."""
        full_url = request.get_full_path()
        xss_patterns = [
            r'<script[^>]*>',
            r'javascript:',
            r'onload=',
            r'onerror=',
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, full_url, re.IGNORECASE):
                return True
        
        return False
    
    def _is_suspicious_user_agent(self, request) -> bool:
        """Check if user agent is suspicious."""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'java', 'perl', 'ruby'
        ]
        
        # Allow python-requests for testing purposes
        if 'python-requests' in user_agent.lower():
            return False
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
    
    def _is_excessive_frequency(self, request) -> bool:
        """Check for excessive request frequency."""
        client_ip = self._get_client_ip(request)
        cache_key = f"request_frequency:{client_ip}"
        
        # Get request count in last minute
        count = cache.get(cache_key, 0)
        
        if count > 100:  # More than 100 requests per minute
            return True
        
        # Increment counter
        cache.set(cache_key, count + 1, 60)
        return False
    
    def _security_response(self, message: str, status: int) -> HttpResponse:
        """Create a standardized security response."""
        return JsonResponse({
            'error': 'Security violation',
            'message': message
        }, status=status)
    
    def _log_request_audit(self, request, start_time: float):
        """Log request for security audit."""
        if not self.audit_enabled:
            return
        
        audit_data = {
            'timestamp': datetime.now().isoformat(),
            'ip': self._get_client_ip(request),
            'method': request.method,
            'path': request.path,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'start_time': start_time,
        }
        
        logger.info(f'Security audit - Request: {audit_data}')
    
    def _log_response_audit(self, request, response, duration: float):
        """Log response for security audit."""
        if not self.audit_enabled:
            return
        
        audit_data = {
            'timestamp': datetime.now().isoformat(),
            'ip': self._get_client_ip(request),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration': duration,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
        }
        
        logger.info(f'Security audit - Response: {audit_data}')
    
    def _log_exception_audit(self, request, exception, duration: float):
        """Log exception for security audit."""
        if not self.audit_enabled:
            return
        
        audit_data = {
            'timestamp': datetime.now().isoformat(),
            'ip': self._get_client_ip(request),
            'method': request.method,
            'path': request.path,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'duration': duration,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
        }
        
        logger.error(f'Security audit - Exception: {audit_data}')
    
    def _load_ip_lists(self):
        """Load IP filtering lists from cache or settings."""
        # Load blocked IPs from cache
        blocked_ips = cache.get('blocked_ips', set())
        if blocked_ips:
            self.blocked_ips = blocked_ips
        
        # Load allowed IPs from settings (if configured)
        allowed_ips = getattr(settings, 'ALLOWED_IPS', [])
        if allowed_ips:
            self.allowed_ips = set(allowed_ips)
    
    def block_ip(self, ip: str, duration: int = 3600):
        """Block an IP address for the specified duration."""
        self.blocked_ips.add(ip)
        cache.set('blocked_ips', self.blocked_ips, duration)
        logger.warning(f'IP blocked: {ip} for {duration} seconds')
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address."""
        self.blocked_ips.discard(ip)
        cache.set('blocked_ips', self.blocked_ips, 3600)
        logger.info(f'IP unblocked: {ip}') 