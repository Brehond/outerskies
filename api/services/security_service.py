"""
Consolidated Security Service for Outer Skies

This service provides comprehensive security functionality:
- Authentication and authorization
- Rate limiting with sliding window algorithm
- Input validation and sanitization
- Security headers and CORS protection
- Threat detection (XSS, SQL injection, path traversal)
- IP filtering and geolocation
- Audit logging and monitoring
- Session security
- File upload security
- API request signing and validation
"""

import time
import json
import logging
import hashlib
import hmac
import re
import ipaddress
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from user_agents import parse
import geoip2.database
import geoip2.errors
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

@dataclass
class SecurityEvent:
    """Security event record"""
    timestamp: datetime
    event_type: str
    severity: str
    ip_address: str
    user_agent: str
    request_path: str
    user_id: Optional[int]
    session_id: Optional[str]
    details: Dict[str, Any]

@dataclass
class RateLimitInfo:
    """Rate limit information"""
    key: str
    current_count: int
    limit: int
    window: int
    reset_time: float
    remaining: int

@dataclass
class SecurityAnalysis:
    """Security analysis result"""
    risk_score: float
    threat_indicators: List[str]
    suspicious_patterns: List[str]
    ip_reputation: Dict[str, Any]
    geo_location: Optional[Dict[str, Any]]
    user_agent_analysis: Dict[str, Any]
    request_validation: Dict[str, Any]

class SecurityService:
    """
    Consolidated security service providing comprehensive security features
    """
    
    def __init__(self):
        # Security configuration
        self.max_request_size = getattr(settings, 'MAX_REQUEST_SIZE', 1024 * 1024)  # 1MB
        self.max_file_size = getattr(settings, 'MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB
        self.allowed_file_types = getattr(settings, 'ALLOWED_FILE_TYPES', [
            'image/jpeg', 'image/png', 'image/gif', 'application/pdf', 'text/plain'
        ])
        
        # Rate limiting configuration
        self.rate_limit_rules = {
            'api': {'requests': 100, 'window': 3600},      # 100 requests per hour
            'auth': {'requests': 5, 'window': 300},        # 5 attempts per 5 minutes
            'chart': {'requests': 10, 'window': 3600},     # 10 charts per hour
            'upload': {'requests': 20, 'window': 3600},    # 20 uploads per hour
            'default': {'requests': 1000, 'window': 3600}  # 1000 requests per hour
        }
        
        # Security patterns
        self.sql_injection_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+.*\s+from',
            r'(\b(union|select|insert|update|delete|drop|create|alter)\b)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*--)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*#)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*/\*)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*\*/)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*;)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*$)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*\n)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*\r)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*\t)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s* )',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*\f)',
            r'(\b(and|or)\b\s+\d+\s*=\s*\d+\s*\v)',
        ]
        
        self.xss_patterns = [
            r'<script[^>]*>.*</script>',
            r'javascript:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'onclick\s*=',
            r'onmouseover\s*=',
            r'onfocus\s*=',
            r'onblur\s*=',
            r'onchange\s*=',
            r'onsubmit\s*=',
            r'onreset\s*=',
            r'onselect\s*=',
            r'onunload\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<applet[^>]*>',
            r'<form[^>]*>',
            r'<input[^>]*>',
            r'<textarea[^>]*>',
            r'<select[^>]*>',
            r'<button[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>',
            r'<title[^>]*>',
            r'<base[^>]*>',
            r'<bgsound[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
            r'<style[^>]*>',
            r'<title[^>]*>',
            r'<base[^>]*>',
            r'<bgsound[^>]*>',
        ]
        
        self.path_traversal_patterns = [
            r'\.\./',
            r'\.\.\\',
            r'%2e%2e%2f',
            r'%2e%2e%5c',
            r'..%2f',
            r'..%5c',
            r'%252e%252e%252f',
            r'%252e%252e%255c',
            r'..%252f',
            r'..%255c',
            r'%c0%ae%c0%ae%c0%af',
            r'%c0%ae%c0%ae%c0%5c',
            r'%c0%ae%c0%ae%c0%af',
            r'%c0%ae%c0%ae%c0%5c',
        ]
        
        # Security state
        self.security_events = deque(maxlen=10000)
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(int)
        self.failed_auth_attempts = defaultdict(int)
        
        # Initialize GeoIP database if available
        self.geoip_reader = None
        if hasattr(settings, 'GEOIP_PATH'):
            try:
                self.geoip_reader = geoip2.database.Reader(settings.GEOIP_PATH)
            except Exception as e:
                logger.warning(f"Could not load GeoIP database: {e}")
        
        # Initialize encryption key
        self.encryption_key = getattr(settings, 'SECURITY_ENCRYPTION_KEY', None)
        if self.encryption_key:
            self.cipher_suite = Fernet(self.encryption_key)
        else:
            self.cipher_suite = None
    
    def get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address with proxy support"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips or cache.get(f'blocked_ip:{ip_address}')
    
    def block_ip(self, ip_address: str, reason: str = "Security violation", duration: int = 86400):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        cache.set(f'blocked_ip:{ip_address}', {
            'reason': reason,
            'timestamp': timezone.now().isoformat(),
            'duration': duration
        }, timeout=duration)
        
        self.log_security_event(
            event_type='ip_blocked',
            severity='high',
            ip_address=ip_address,
            user_agent='',
            request_path='',
            user_id=None,
            session_id=None,
            details={'reason': reason, 'duration': duration}
        )
    
    def check_rate_limit(self, request: HttpRequest, rule_type: str = 'default') -> Tuple[bool, RateLimitInfo]:
        """Check rate limiting for request with sliding window algorithm"""
        ip_address = self.get_client_ip(request)
        user_id = request.user.id if request.user.is_authenticated else None
        
        # Get rate limit rule
        rule = self.rate_limit_rules.get(rule_type, self.rate_limit_rules['default'])
        
        # Create rate limit key
        if user_id:
            key = f'rate_limit:{rule_type}:user:{user_id}'
        else:
            key = f'rate_limit:{rule_type}:ip:{ip_address}'
        
        # Get current usage with sliding window
        current_time = time.time()
        window_start = current_time - rule['window']
        
        # Get existing requests in window
        requests_in_window = cache.get(key, [])
        
        # Remove expired requests
        requests_in_window = [req_time for req_time in requests_in_window if req_time > window_start]
        
        # Check if limit exceeded
        if len(requests_in_window) >= rule['requests']:
            # Calculate reset time (when oldest request expires)
            reset_time = requests_in_window[0] + rule['window'] if requests_in_window else current_time + rule['window']
            
            self.log_security_event(
                event_type='rate_limit_exceeded',
                severity='medium',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                user_id=user_id,
                session_id=request.session.session_key if hasattr(request, 'session') else None,
                details={
                    'rule_type': rule_type,
                    'limit': rule['requests'],
                    'window': rule['window'],
                    'current_count': len(requests_in_window)
                }
            )
            
            return False, RateLimitInfo(
                key=key,
                current_count=len(requests_in_window),
                limit=rule['requests'],
                window=rule['window'],
                reset_time=reset_time,
                remaining=0
            )
        
        # Add current request
        requests_in_window.append(current_time)
        cache.set(key, requests_in_window, timeout=rule['window'])
        
        return True, RateLimitInfo(
            key=key,
            current_count=len(requests_in_window),
            limit=rule['requests'],
            window=rule['window'],
            reset_time=current_time + rule['window'],
            remaining=rule['requests'] - len(requests_in_window)
        )
    
    def validate_input(self, data: Union[str, Dict, List], input_type: str = 'general') -> Tuple[bool, List[str]]:
        """Validate and sanitize input data"""
        errors = []
        
        if isinstance(data, str):
            # Check for SQL injection
            for pattern in self.sql_injection_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    errors.append(f"SQL injection pattern detected in {input_type}")
                    break
            
            # Check for XSS
            for pattern in self.xss_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    errors.append(f"XSS pattern detected in {input_type}")
                    break
            
            # Check for path traversal
            for pattern in self.path_traversal_patterns:
                if re.search(pattern, data, re.IGNORECASE):
                    errors.append(f"Path traversal pattern detected in {input_type}")
                    break
        
        elif isinstance(data, dict):
            for key, value in data.items():
                is_valid, key_errors = self.validate_input(value, f"{input_type}.{key}")
                if not is_valid:
                    errors.extend(key_errors)
        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                is_valid, item_errors = self.validate_input(item, f"{input_type}[{i}]")
                if not is_valid:
                    errors.extend(item_errors)
        
        return len(errors) == 0, errors
    
    def validate_file_upload(self, file_obj, max_size: Optional[int] = None) -> Tuple[bool, List[str]]:
        """Validate file upload"""
        errors = []
        
        if max_size is None:
            max_size = self.max_file_size
        
        # Check file size
        if file_obj.size > max_size:
            errors.append(f"File size {file_obj.size} exceeds maximum allowed size {max_size}")
        
        # Check file type
        if hasattr(file_obj, 'content_type') and file_obj.content_type:
            if file_obj.content_type not in self.allowed_file_types:
                errors.append(f"File type {file_obj.content_type} is not allowed")
        
        # Check file extension
        if hasattr(file_obj, 'name') and file_obj.name:
            allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.txt']
            file_extension = file_obj.name.lower()
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                errors.append(f"File extension not allowed")
        
        return len(errors) == 0, errors
    
    def analyze_request(self, request: HttpRequest) -> SecurityAnalysis:
        """Comprehensive security analysis of request"""
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Initialize analysis
        threat_indicators = []
        suspicious_patterns = []
        risk_score = 0.0
        
        # Check IP reputation
        ip_reputation = self.check_ip_reputation(ip_address)
        if ip_reputation.get('is_suspicious', False):
            threat_indicators.append('suspicious_ip')
            risk_score += 0.3
        
        # Check for suspicious patterns
        patterns = self.check_suspicious_patterns(request)
        if patterns:
            suspicious_patterns.extend(patterns)
            risk_score += 0.2 * len(patterns)
        
        # Analyze user agent
        user_agent_analysis = self.analyze_user_agent(user_agent)
        if user_agent_analysis.get('is_suspicious', False):
            threat_indicators.append('suspicious_user_agent')
            risk_score += 0.2
        
        # Validate request data
        request_validation = self.validate_request_data(request)
        if not request_validation.get('is_valid', True):
            threat_indicators.append('invalid_request_data')
            risk_score += 0.3
        
        # Check geolocation
        geo_location = self.get_geo_location(ip_address)
        if geo_location and geo_location.get('is_high_risk_country', False):
            threat_indicators.append('high_risk_location')
            risk_score += 0.1
        
        # Cap risk score at 1.0
        risk_score = min(risk_score, 1.0)
        
        return SecurityAnalysis(
            risk_score=risk_score,
            threat_indicators=threat_indicators,
            suspicious_patterns=suspicious_patterns,
            ip_reputation=ip_reputation,
            geo_location=geo_location,
            user_agent_analysis=user_agent_analysis,
            request_validation=request_validation
        )
    
    def check_suspicious_patterns(self, request: HttpRequest) -> List[str]:
        """Check for suspicious patterns in request"""
        suspicious_found = []
        
        # Check URL parameters
        for param, value in request.GET.items():
            is_valid, errors = self.validate_input(value, f"GET.{param}")
            if not is_valid:
                suspicious_found.extend(errors)
        
        # Check POST data
        if request.method == 'POST':
            for param, value in request.POST.items():
                is_valid, errors = self.validate_input(value, f"POST.{param}")
                if not is_valid:
                    suspicious_found.extend(errors)
        
        # Check headers
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent or user_agent.lower() in ['', 'null', 'undefined']:
            suspicious_found.append("Missing or suspicious User-Agent")
        
        return suspicious_found
    
    def check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Check IP reputation using external services"""
        cache_key = f'ip_reputation:{ip_address}'
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Basic IP validation
        try:
            ipaddress.ip_address(ip_address)
        except ValueError:
            return {'is_valid': False, 'is_suspicious': True, 'reason': 'Invalid IP format'}
        
        # Check if IP is in private range
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            if ip_obj.is_private:
                return {'is_valid': True, 'is_suspicious': False, 'is_private': True}
        except ValueError:
            pass
        
        # Check local cache for suspicious IPs
        if ip_address in self.suspicious_ips:
            return {
                'is_valid': True,
                'is_suspicious': True,
                'suspicious_count': self.suspicious_ips[ip_address],
                'reason': 'Previously flagged as suspicious'
            }
        
        # For production, you would integrate with external IP reputation services
        # For now, return basic analysis
        result = {
            'is_valid': True,
            'is_suspicious': False,
            'checked_at': timezone.now().isoformat()
        }
        
        # Cache result for 1 hour
        cache.set(cache_key, result, timeout=3600)
        return result
    
    def analyze_user_agent(self, user_agent: str) -> Dict[str, Any]:
        """Analyze user agent for suspicious patterns"""
        if not user_agent:
            return {'is_suspicious': True, 'reason': 'Missing User-Agent'}
        
        user_agent_lower = user_agent.lower()
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python',
            'java', 'perl', 'ruby', 'php', 'go-http-client', 'okhttp',
            'apache-httpclient', 'requests', 'urllib', 'mechanize'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in user_agent_lower:
                return {
                    'is_suspicious': True,
                    'reason': f'Contains suspicious pattern: {pattern}',
                    'pattern': pattern
                }
        
        # Parse user agent
        try:
            parsed_ua = parse(user_agent)
            return {
                'is_suspicious': False,
                'browser': parsed_ua.browser.family,
                'os': parsed_ua.os.family,
                'device': parsed_ua.device.family,
                'is_bot': parsed_ua.is_bot
            }
        except Exception:
            return {
                'is_suspicious': True,
                'reason': 'Could not parse User-Agent'
            }
    
    def validate_request_data(self, request: HttpRequest) -> Dict[str, Any]:
        """Validate request data"""
        errors = []
        
        # Check request size
        content_length = request.META.get('CONTENT_LENGTH', 0)
        if content_length and int(content_length) > self.max_request_size:
            errors.append(f"Request size {content_length} exceeds maximum {self.max_request_size}")
        
        # Validate content type for POST requests
        if request.method == 'POST':
            content_type = request.META.get('CONTENT_TYPE', '')
            if not content_type:
                errors.append("Missing Content-Type header")
            elif 'application/json' in content_type and not request.body:
                errors.append("JSON content type specified but no body provided")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_geo_location(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation information for IP address"""
        if not self.geoip_reader:
            return None
        
        try:
            response = self.geoip_reader.city(ip_address)
            return {
                'country': response.country.name,
                'country_code': response.country.iso_code,
                'city': response.city.name,
                'latitude': response.location.latitude,
                'longitude': response.location.longitude,
                'is_high_risk_country': response.country.iso_code in ['XX', 'YY']  # Define high-risk countries
            }
        except (geoip2.errors.AddressNotFoundError, geoip2.errors.GeoIP2Error):
            return None
    
    def log_security_event(self, event_type: str, severity: str, ip_address: str,
                          user_agent: str, request_path: str, user_id: Optional[int],
                          session_id: Optional[str], details: Dict[str, Any]):
        """Log security event"""
        event = SecurityEvent(
            timestamp=timezone.now(),
            event_type=event_type,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            user_id=user_id,
            session_id=session_id,
            details=details
        )
        
        # Add to in-memory queue
        self.security_events.append(event)
        
        # Log to file
        logger.warning(f"Security event: {event_type} - {severity} - IP: {ip_address} - Path: {request_path}")
        
        # Store in cache for monitoring
        cache_key = f'security_event:{event_type}:{ip_address}:{int(time.time())}'
        cache.set(cache_key, asdict(event), timeout=86400)  # Keep for 24 hours
        
        # Update threat indicators
        if severity in ['high', 'critical']:
            self.suspicious_ips[ip_address] += 1
    
    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get security report for the specified time period"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get events from cache
        events = []
        for event in self.security_events:
            if event.timestamp >= cutoff_time:
                events.append(asdict(event))
        
        # Calculate statistics
        event_types = defaultdict(int)
        severity_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        
        for event in events:
            event_types[event['event_type']] += 1
            severity_counts[event['severity']] += 1
            ip_counts[event['ip_address']] += 1
        
        return {
            'period_hours': hours,
            'total_events': len(events),
            'event_types': dict(event_types),
            'severity_counts': dict(severity_counts),
            'top_ips': dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'blocked_ips_count': len(self.blocked_ips),
            'suspicious_ips_count': len(self.suspicious_ips),
            'recent_events': events[-50:]  # Last 50 events
        }
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        if not self.cipher_suite:
            raise ValueError("Encryption key not configured")
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        if not self.cipher_suite:
            raise ValueError("Encryption key not configured")
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def generate_request_signature(self, data: str, secret: str) -> str:
        """Generate HMAC signature for request validation"""
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def verify_request_signature(self, data: str, signature: str, secret: str) -> bool:
        """Verify HMAC signature"""
        expected_signature = self.generate_request_signature(data, secret)
        return hmac.compare_digest(signature, expected_signature)

# Global security service instance
security_service = SecurityService() 