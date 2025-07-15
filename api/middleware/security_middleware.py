"""
Enhanced Security Middleware

This module provides comprehensive security features:
- Rate limiting and throttling
- Input validation and sanitization
- Security headers
- CORS protection
- Request logging and monitoring
- IP filtering and geolocation
"""

import time
import json
import logging
import hashlib
import re
from typing import Dict, Any, Optional, List
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError
import ipaddress
from user_agents import parse
import redis

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""
    
    def process_response(self, request, response):
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware with IP-based and user-based limits"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.rate_limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'api': {'requests': 1000, 'window': 3600},     # 1000 API requests per hour
            'chart_generation': {'requests': 10, 'window': 3600},  # 10 charts per hour
            'auth': {'requests': 5, 'window': 300},        # 5 auth attempts per 5 minutes
        }
    
    def process_request(self, request):
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Determine rate limit type
        rate_limit_type = self._get_rate_limit_type(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_ip, rate_limit_type):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': f'Too many requests. Limit: {self.rate_limits[rate_limit_type]["requests"]} per {self.rate_limits[rate_limit_type]["window"]}s'
            }, status=429)
        
        return None
    
    def _get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _get_rate_limit_type(self, request):
        """Determine rate limit type based on request"""
        path = request.path.lower()
        
        if '/api/v1/auth/' in path:
            return 'auth'
        elif '/api/v1/charts/generate' in path:
            return 'chart_generation'
        elif '/api/' in path:
            return 'api'
        else:
            return 'default'
    
    def _check_rate_limit(self, client_ip: str, rate_limit_type: str) -> bool:
        """Check if request is within rate limit"""
        limit_config = self.rate_limits[rate_limit_type]
        cache_key = f"rate_limit:{rate_limit_type}:{client_ip}"
        
        # Get current request count
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit_config['requests']:
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, limit_config['window'])
        return True


class InputValidationMiddleware(MiddlewareMixin):
    """Input validation and sanitization middleware"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
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
        
        self.max_request_size = 10 * 1024 * 1024  # 10MB
    
    def process_request(self, request):
        # Check request size
        content_length = request.META.get('CONTENT_LENGTH', 0)
        if content_length and int(content_length) > self.max_request_size:
            return JsonResponse({
                'error': 'Request too large',
                'message': f'Request size exceeds maximum allowed size of {self.max_request_size // (1024*1024)}MB'
            }, status=413)
        
        # Validate and sanitize input
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                self._validate_request_data(request)
            except ValidationError as e:
                return JsonResponse({
                    'error': 'Invalid input',
                    'message': str(e)
                }, status=400)
        
        return None
    
    def _validate_request_data(self, request):
        """Validate and sanitize request data"""
        # Check for suspicious patterns in headers
        for header_name, header_value in request.META.items():
            if isinstance(header_value, str) and self._contains_suspicious_content(header_value):
                raise ValidationError(f'Suspicious content detected in header: {header_name}')
        
        # Validate JSON data
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body.decode('utf-8'))
                self._sanitize_data(data)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON data')
        
        # Validate form data
        elif request.content_type == 'application/x-www-form-urlencoded':
            for key, value in request.POST.items():
                if isinstance(value, str) and self._contains_suspicious_content(value):
                    raise ValidationError(f'Suspicious content detected in field: {key}')
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """Check if content contains suspicious patterns"""
        content_lower = content.lower()
        for pattern in self.suspicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                return True
        return False
    
    def _sanitize_data(self, data: Any):
        """Recursively sanitize data"""
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


class CORSMiddleware(MiddlewareMixin):
    """CORS protection middleware"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.allowed_origins = getattr(settings, 'ALLOWED_CORS_ORIGINS', [
            'http://localhost:3000',
            'http://127.0.0.1:3000',
            'https://outer-skies.com',
            'https://www.outer-skies.com'
        ])
        self.allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
        self.allowed_headers = [
            'Content-Type', 'Authorization', 'X-API-Key', 
            'X-Requested-With', 'Accept', 'Origin'
        ]
    
    def process_request(self, request):
        # Handle preflight requests
        if request.method == 'OPTIONS':
            return self._handle_preflight(request)
        
        # Check origin for actual requests
        origin = request.META.get('HTTP_ORIGIN')
        if origin and origin not in self.allowed_origins:
            return JsonResponse({
                'error': 'CORS policy violation',
                'message': 'Origin not allowed'
            }, status=403)
        
        return None
    
    def process_response(self, request, response):
        # Add CORS headers
        origin = request.META.get('HTTP_ORIGIN')
        if origin in self.allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
            response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
        
        return response
    
    def _handle_preflight(self, request):
        """Handle CORS preflight requests"""
        origin = request.META.get('HTTP_ORIGIN')
        if origin not in self.allowed_origins:
            return JsonResponse({'error': 'CORS policy violation'}, status=403)
        
        response = JsonResponse({})
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
        response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """Request logging and monitoring middleware"""
    
    def process_request(self, request):
        # Add request start time
        request.start_time = time.time()
        
        # Log request details
        self._log_request(request)
        
        return None
    
    def process_response(self, request, response):
        # Calculate request duration
        duration = time.time() - request.start_time
        
        # Log response details
        self._log_response(request, response, duration)
        
        return response
    
    def process_exception(self, request, exception):
        # Log exceptions
        duration = time.time() - request.start_time
        self._log_exception(request, exception, duration)
        
        return None
    
    def _log_request(self, request):
        """Log incoming request details"""
        user_agent = parse(request.META.get('HTTP_USER_AGENT', ''))
        client_ip = self._get_client_ip(request)
        
        log_data = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'client_ip': client_ip,
            'user_agent': {
                'browser': user_agent.browser.family,
                'os': user_agent.os.family,
                'device': user_agent.device.family
            },
            'content_type': request.content_type,
            'content_length': request.META.get('CONTENT_LENGTH', 0)
        }
        
        logger.info(f"Request: {request.method} {request.path} from {client_ip}", extra=log_data)
    
    def _log_response(self, request, response, duration):
        """Log response details"""
        log_data = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'content_length': len(response.content) if hasattr(response, 'content') else 0
        }
        
        logger.info(f"Response: {response.status_code} in {log_data['duration_ms']}ms", extra=log_data)
    
    def _log_exception(self, request, exception, duration):
        """Log exception details"""
        log_data = {
            'timestamp': time.time(),
            'method': request.method,
            'path': request.path,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'duration_ms': round(duration * 1000, 2)
        }
        
        logger.error(f"Exception: {exception}", extra=log_data)
    
    def _get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class IPFilterMiddleware(MiddlewareMixin):
    """IP filtering and geolocation middleware"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.blocked_ips = getattr(settings, 'BLOCKED_IPS', [])
        self.allowed_ips = getattr(settings, 'ALLOWED_IPS', [])
        self.geo_blocked_countries = getattr(settings, 'GEO_BLOCKED_COUNTRIES', [])
    
    def process_request(self, request):
        client_ip = self._get_client_ip(request)
        
        # Check if IP is blocked
        if self._is_ip_blocked(client_ip):
            return JsonResponse({
                'error': 'Access denied',
                'message': 'Your IP address is not allowed'
            }, status=403)
        
        # Check if IP is in allowed list (if whitelist is enabled)
        if self.allowed_ips and not self._is_ip_allowed(client_ip):
            return JsonResponse({
                'error': 'Access denied',
                'message': 'Your IP address is not in the allowed list'
            }, status=403)
        
        # Add geolocation info to request
        request.geo_info = self._get_geo_info(client_ip)
        
        return None
    
    def _get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is in blocked list"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for blocked_ip in self.blocked_ips:
                if ip_obj in ipaddress.ip_network(blocked_ip):
                    return True
        except ValueError:
            pass
        return False
    
    def _is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is in allowed list"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            for allowed_ip in self.allowed_ips:
                if ip_obj in ipaddress.ip_network(allowed_ip):
                    return True
        except ValueError:
            pass
        return False
    
    def _get_geo_info(self, ip: str) -> Dict[str, Any]:
        """Get geolocation information for IP"""
        # This would integrate with a geolocation service
        # For now, return basic info
        return {
            'ip': ip,
            'country': 'Unknown',
            'city': 'Unknown',
            'timezone': 'UTC'
        }


class SecurityAuditMiddleware(MiddlewareMixin):
    """Security audit and monitoring middleware"""
    
    def process_request(self, request):
        # Check for security violations
        violations = self._check_security_violations(request)
        
        if violations:
            # Log security violations
            self._log_security_violations(request, violations)
            
            # Return error for critical violations
            if any(v['severity'] == 'critical' for v in violations):
                return JsonResponse({
                    'error': 'Security violation detected',
                    'message': 'Request blocked due to security policy'
                }, status=403)
        
        return None
    
    def _check_security_violations(self, request) -> List[Dict[str, Any]]:
        """Check for security violations"""
        violations = []
        
        # Check for suspicious user agents
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if self._is_suspicious_user_agent(user_agent):
            violations.append({
                'type': 'suspicious_user_agent',
                'severity': 'warning',
                'details': f'Suspicious user agent: {user_agent[:100]}'
            })
        
        # Check for suspicious request patterns
        if self._has_suspicious_patterns(request):
            violations.append({
                'type': 'suspicious_patterns',
                'severity': 'critical',
                'details': 'Suspicious request patterns detected'
            })
        
        # Check for excessive request frequency
        if self._is_excessive_frequency(request):
            violations.append({
                'type': 'excessive_frequency',
                'severity': 'warning',
                'details': 'Excessive request frequency detected'
            })
        
        return violations
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'java', 'perl', 'ruby'
        ]
        
        # Allow python-requests for testing purposes
        if 'python-requests' in user_agent.lower():
            return False
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)
    
    def _has_suspicious_patterns(self, request) -> bool:
        """Check for suspicious request patterns"""
        # Check for SQL injection patterns
        sql_patterns = [
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(or|and)\b\s+\d+\s*=\s*\d+)',
            r'(\b(union|select)\b.*\bfrom\b)',
        ]
        
        # Check URL and parameters
        full_url = request.get_full_path()
        for pattern in sql_patterns:
            if re.search(pattern, full_url, re.IGNORECASE):
                return True
        
        return False
    
    def _is_excessive_frequency(self, request) -> bool:
        """Check for excessive request frequency"""
        client_ip = self._get_client_ip(request)
        cache_key = f"request_frequency:{client_ip}"
        
        # Get request count in last minute
        count = cache.get(cache_key, 0)
        
        if count > 100:  # More than 100 requests per minute
            return True
        
        # Increment counter
        cache.set(cache_key, count + 1, 60)
        return False
    
    def _log_security_violations(self, request, violations):
        """Log security violations"""
        for violation in violations:
            log_data = {
                'timestamp': time.time(),
                'client_ip': self._get_client_ip(request),
                'method': request.method,
                'path': request.path,
                'violation_type': violation['type'],
                'severity': violation['severity'],
                'details': violation['details']
            }
            
            if violation['severity'] == 'critical':
                logger.critical(f"Security violation: {violation['type']}", extra=log_data)
            else:
                logger.warning(f"Security warning: {violation['type']}", extra=log_data)
    
    def _get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown') 