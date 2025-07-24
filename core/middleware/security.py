"""
Consolidated Security Middleware for Outer Skies

This module provides a single, comprehensive security middleware that
replaces the fragmented security middlewares across the application.
"""

import logging
import time
import json
import hashlib
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User

from ..exceptions import (
    SecurityError, IPBlockedError, RateLimitExceededError, 
    SuspiciousActivityError, AuthenticationError
)
from ..error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Consolidated security middleware that handles all security concerns.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.security_chain = [
            self._rate_limit_check,
            self._authentication_check,
            self._authorization_check,
            self._input_validation,
            self._threat_detection,
            self._security_headers
        ]
        
        # Security configuration
        self.rate_limit_rules = {
            'api': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'auth': {'requests': 5, 'window': 300},    # 5 attempts per 5 minutes
            'chart': {'requests': 10, 'window': 3600}, # 10 charts per hour
            'default': {'requests': 1000, 'window': 3600}  # 1000 requests per hour
        }
        
        self.blocked_ips = set()
        self.suspicious_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+.*\s+from',
            r'<script[^>]*>.*</script>',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>'
        ]
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.time()
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Run security chain
        for security_check in self.security_chain:
            try:
                result = security_check(request, client_ip)
                if result:  # If security check returns a response, block the request
                    return result
            except Exception as e:
                logger.error(f"Security check failed: {e}")
                # Continue with other checks, don't fail completely
        
        # Process request
        try:
            response = self.get_response(request)
        except Exception as e:
            # Log security-relevant exceptions
            self._log_security_event(
                event_type='request_exception',
                severity='medium',
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                user_id=request.user.id if request.user.is_authenticated else None,
                details={'exception': str(e), 'exception_type': type(e).__name__}
            )
            raise
        
        # Add security headers
        response = self._add_security_headers(response)
        
        # Log request metrics
        self._log_request_metrics(request, response, start_time, client_ip)
        
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address with proxy support."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _rate_limit_check(self, request: HttpRequest, client_ip: str) -> Optional[HttpResponse]:
        """Check rate limiting for request."""
        rate_limit_type = self._determine_rate_limit_type(request)
        rate_limit_ok, rate_limit_info = self._check_rate_limit(request, rate_limit_type, client_ip)
        
        if not rate_limit_ok:
            return self._create_rate_limit_response(request, rate_limit_info)
        
        return None
    
    def _authentication_check(self, request: HttpRequest, client_ip: str) -> Optional[HttpResponse]:
        """Check authentication requirements."""
        # Skip for public endpoints
        if self._is_public_endpoint(request.path):
            return None
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return self._create_authentication_response(request)
        
        return None
    
    def _authorization_check(self, request: HttpRequest, client_ip: str) -> Optional[HttpResponse]:
        """Check authorization for the request."""
        # Skip for public endpoints
        if self._is_public_endpoint(request.path):
            return None
        
        # Check if user has required permissions
        if not self._has_required_permissions(request):
            return self._create_authorization_response(request)
        
        return None
    
    def _input_validation(self, request: HttpRequest, client_ip: str) -> Optional[HttpResponse]:
        """Validate and sanitize input."""
        # Check for suspicious patterns
        suspicious_patterns = self._check_suspicious_patterns(request)
        if suspicious_patterns:
            self._log_security_event(
                event_type='suspicious_patterns',
                severity='medium',
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                user_id=request.user.id if request.user.is_authenticated else None,
                details={'patterns': suspicious_patterns}
            )
        
        return None
    
    def _threat_detection(self, request: HttpRequest, client_ip: str) -> Optional[HttpResponse]:
        """Detect potential threats."""
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            return self._create_blocked_response(request, "IP address is blocked")
        
        # Check for unusual activity
        if self._is_unusual_activity(client_ip, request):
            self._log_security_event(
                event_type='unusual_activity',
                severity='high',
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                user_id=request.user.id if request.user.is_authenticated else None,
                details={'activity_type': 'unusual_pattern'}
            )
        
        return None
    
    def _security_headers(self, request: HttpRequest, client_ip: str) -> Optional[HttpResponse]:
        """Add security headers to request."""
        # Add security context to request
        request.security_context = {
            'client_ip': client_ip,
            'risk_score': self._calculate_risk_score(request, client_ip),
            'threat_indicators': self._get_threat_indicators(request, client_ip)
        }
        
        return None
    
    def _determine_rate_limit_type(self, request: HttpRequest) -> str:
        """Determine the appropriate rate limit type for the request."""
        path = request.path.lower()
        
        if '/api/' in path:
            if '/auth/' in path or '/login' in path or '/register' in path:
                return 'auth'
            elif '/chart/' in path or '/generate' in path:
                return 'chart'
            else:
                return 'api'
        elif '/chart/' in path:
            return 'chart'
        else:
            return 'default'
    
    def _check_rate_limit(self, request: HttpRequest, rule_type: str, client_ip: str) -> tuple:
        """Check rate limiting for request."""
        user_id = request.user.id if request.user.is_authenticated else None
        
        # Get rate limit rule
        rule = self.rate_limit_rules.get(rule_type, self.rate_limit_rules['default'])
        
        # Create rate limit key
        if user_id:
            key = f'rate_limit:{rule_type}:user:{user_id}'
        else:
            key = f'rate_limit:{rule_type}:ip:{client_ip}'
        
        # Get current usage
        usage = cache.get(key, {'count': 0, 'reset_time': time.time() + rule['window']})
        
        # Check if window has reset
        if time.time() > usage['reset_time']:
            usage = {'count': 0, 'reset_time': time.time() + rule['window']}
        
        # Check if limit exceeded
        if usage['count'] >= rule['requests']:
            return False, {
                'limit_exceeded': True,
                'limit': rule['requests'],
                'window': rule['window'],
                'reset_time': usage['reset_time']
            }
        
        # Increment usage
        usage['count'] += 1
        cache.set(key, usage, timeout=rule['window'])
        
        return True, {
            'limit_exceeded': False,
            'current_count': usage['count'],
            'limit': rule['requests'],
            'remaining': rule['requests'] - usage['count']
        }
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no auth required)."""
        public_paths = [
            '/api/v1/health/',
            '/api/v1/system/health/',
            '/static/',
            '/media/',
            '/favicon.ico',
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    def _has_required_permissions(self, request: HttpRequest) -> bool:
        """Check if user has required permissions."""
        # Basic permission check - can be extended
        if request.user.is_staff:
            return True
        
        # Add more specific permission checks here
        return True
    
    def _check_suspicious_patterns(self, request: HttpRequest) -> List[str]:
        """Check for suspicious patterns in request."""
        suspicious_found = []
        
        # Check URL parameters
        for param, value in request.GET.items():
            for pattern in self.suspicious_patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    suspicious_found.append(f"URL parameter '{param}' contains suspicious pattern")
        
        # Check POST data
        if request.method == 'POST':
            for param, value in request.POST.items():
                if isinstance(value, str):
                    for pattern in self.suspicious_patterns:
                        if re.search(pattern, value, re.IGNORECASE):
                            suspicious_found.append(f"POST parameter '{param}' contains suspicious pattern")
        
        # Check headers
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent or user_agent.lower() in ['', 'null', 'undefined']:
            suspicious_found.append("Missing or suspicious User-Agent")
        
        return suspicious_found
    
    def _is_unusual_activity(self, client_ip: str, request: HttpRequest) -> bool:
        """Check for unusual activity patterns."""
        # Simple check - can be enhanced with ML/analytics
        recent_requests = cache.get(f'recent_requests:{client_ip}', [])
        current_time = time.time()
        
        # Remove old requests (older than 1 hour)
        recent_requests = [req for req in recent_requests if current_time - req < 3600]
        
        # Add current request
        recent_requests.append(current_time)
        cache.set(f'recent_requests:{client_ip}', recent_requests, timeout=3600)
        
        # Check for high frequency requests
        if len(recent_requests) > 100:  # More than 100 requests per hour
            return True
        
        return False
    
    def _calculate_risk_score(self, request: HttpRequest, client_ip: str) -> float:
        """Calculate risk score for the request."""
        risk_score = 0.0
        
        # Check for suspicious patterns
        suspicious_patterns = self._check_suspicious_patterns(request)
        risk_score += len(suspicious_patterns) * 0.2
        
        # Check for unusual activity
        if self._is_unusual_activity(client_ip, request):
            risk_score += 0.3
        
        # Check for missing authentication on protected endpoints
        if not self._is_public_endpoint(request.path) and not request.user.is_authenticated:
            risk_score += 0.5
        
        return min(risk_score, 1.0)
    
    def _get_threat_indicators(self, request: HttpRequest, client_ip: str) -> List[str]:
        """Get threat indicators for the request."""
        indicators = []
        
        # Check for suspicious patterns
        suspicious_patterns = self._check_suspicious_patterns(request)
        if suspicious_patterns:
            indicators.extend(suspicious_patterns)
        
        # Check for unusual activity
        if self._is_unusual_activity(client_ip, request):
            indicators.append("unusual_activity")
        
        # Check for missing authentication
        if not self._is_public_endpoint(request.path) and not request.user.is_authenticated:
            indicators.append("missing_authentication")
        
        return indicators
    
    def _create_blocked_response(self, request: HttpRequest, reason: str) -> HttpResponse:
        """Create a response for blocked requests."""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Access denied',
                'reason': reason,
                'timestamp': timezone.now().isoformat(),
                'request_id': self._generate_request_id(request)
            }, status=403)
        else:
            return HttpResponse(
                f"Access denied: {reason}",
                status=403,
                content_type='text/plain'
            )
    
    def _create_rate_limit_response(self, request: HttpRequest, rate_limit_info: Dict[str, Any]) -> HttpResponse:
        """Create a response for rate-limited requests."""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'limit': rate_limit_info['limit'],
                'window': rate_limit_info['window'],
                'reset_time': rate_limit_info['reset_time'],
                'timestamp': timezone.now().isoformat(),
                'request_id': self._generate_request_id(request)
            }, status=429)
        else:
            return HttpResponse(
                "Rate limit exceeded. Please try again later.",
                status=429,
                content_type='text/plain'
            )
    
    def _create_authentication_response(self, request: HttpRequest) -> HttpResponse:
        """Create a response for authentication failures."""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Please log in to access this resource',
                'timestamp': timezone.now().isoformat(),
                'request_id': self._generate_request_id(request)
            }, status=401)
        else:
            return HttpResponse(
                "Authentication required. Please log in.",
                status=401,
                content_type='text/plain'
            )
    
    def _create_authorization_response(self, request: HttpRequest) -> HttpResponse:
        """Create a response for authorization failures."""
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Access denied',
                'message': 'You do not have permission to access this resource',
                'timestamp': timezone.now().isoformat(),
                'request_id': self._generate_request_id(request)
            }, status=403)
        else:
            return HttpResponse(
                "Access denied. You do not have permission to access this resource.",
                status=403,
                content_type='text/plain'
            )
    
    def _add_security_headers(self, response: HttpResponse) -> HttpResponse:
        """Add security headers to response."""
        # Standard security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        
        # Custom security headers
        if hasattr(response, 'security_context'):
            security_context = response.security_context
            response['X-Security-Risk-Score'] = str(security_context.get('risk_score', 0))
            response['X-Security-Threat-Indicators'] = ','.join(security_context.get('threat_indicators', []))
        
        return response
    
    def _log_security_event(self, event_type: str, severity: str, ip_address: str,
                           user_agent: str, request_path: str, user_id: Optional[int],
                           details: Dict[str, Any]):
        """Log security events."""
        log_data = {
            'event_type': event_type,
            'severity': severity,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'request_path': request_path,
            'user_id': user_id,
            'timestamp': timezone.now().isoformat(),
            'details': details
        }
        
        if severity == 'high':
            logger.error(f"Security event: {event_type}", extra=log_data)
        elif severity == 'medium':
            logger.warning(f"Security event: {event_type}", extra=log_data)
        else:
            logger.info(f"Security event: {event_type}", extra=log_data)
    
    def _log_request_metrics(self, request: HttpRequest, response: HttpResponse, 
                           start_time: float, client_ip: str):
        """Log request metrics for monitoring."""
        duration = time.time() - start_time
        
        # Update request statistics in cache
        request_stats = cache.get('request_stats', {
            'total_requests': 0,
            'errors': 0,
            'total_duration': 0.0,
            'avg_response_time': 0.0
        })
        
        request_stats['total_requests'] += 1
        request_stats['total_duration'] += duration
        
        if response.status_code >= 400:
            request_stats['errors'] += 1
        
        # Calculate average response time
        if request_stats['total_requests'] > 0:
            request_stats['avg_response_time'] = request_stats['total_duration'] / request_stats['total_requests']
        
        cache.set('request_stats', request_stats, timeout=3600)
    
    def _generate_request_id(self, request: HttpRequest) -> str:
        """Generate a unique request ID."""
        return hashlib.md5(f"{request.path}{time.time()}".encode()).hexdigest()[:8] 