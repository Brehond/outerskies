"""
Advanced Security System for Outer Skies
Comprehensive security features including rate limiting, threat detection, and IP reputation
"""

import logging
import time
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import ipaddress
import requests
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
import geoip2.database
import geoip2.errors

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
    details: Dict[str, Any]

@dataclass
class ThreatIndicator:
    """Threat indicator"""
    ip_address: str
    threat_type: str
    confidence: float
    first_seen: datetime
    last_seen: datetime
    event_count: int
    details: Dict[str, Any]

class AdvancedSecuritySystem:
    """
    Advanced security system with comprehensive threat detection
    """
    
    def __init__(self):
        self.security_events = deque(maxlen=10000)
        self.threat_indicators = {}
        self.ip_reputation_cache = {}
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
        
        # Initialize GeoIP database if available
        self.geoip_reader = None
        if hasattr(settings, 'GEOIP_PATH'):
            try:
                self.geoip_reader = geoip2.database.Reader(settings.GEOIP_PATH)
            except Exception as e:
                logger.warning(f"Could not load GeoIP database: {e}")
    
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
        return ip_address in self.blocked_ips
    
    def block_ip(self, ip_address: str, reason: str = "Security violation"):
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        cache.set(f'blocked_ip:{ip_address}', {
            'reason': reason,
            'timestamp': timezone.now().isoformat()
        }, timeout=86400)  # Block for 24 hours
        
        self.log_security_event(
            event_type='ip_blocked',
            severity='high',
            ip_address=ip_address,
            user_agent='',
            request_path='',
            user_id=None,
            details={'reason': reason}
        )
    
    def check_rate_limit(self, request: HttpRequest, rule_type: str = 'default') -> Tuple[bool, Dict[str, Any]]:
        """Check rate limiting for request"""
        ip_address = self.get_client_ip(request)
        user_id = request.user.id if request.user.is_authenticated else None
        
        # Get rate limit rule
        rule = self.rate_limit_rules.get(rule_type, self.rate_limit_rules['default'])
        
        # Create rate limit key
        if user_id:
            key = f'rate_limit:{rule_type}:user:{user_id}'
        else:
            key = f'rate_limit:{rule_type}:ip:{ip_address}'
        
        # Get current usage
        usage = cache.get(key, {'count': 0, 'reset_time': time.time() + rule['window']})
        
        # Check if window has reset
        if time.time() > usage['reset_time']:
            usage = {'count': 0, 'reset_time': time.time() + rule['window']}
        
        # Check if limit exceeded
        if usage['count'] >= rule['requests']:
            self.log_security_event(
                event_type='rate_limit_exceeded',
                severity='medium',
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                request_path=request.path,
                user_id=user_id,
                details={
                    'rule_type': rule_type,
                    'limit': rule['requests'],
                    'window': rule['window'],
                    'current_count': usage['count']
                }
            )
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
    
    def check_suspicious_patterns(self, request: HttpRequest) -> List[str]:
        """Check for suspicious patterns in request"""
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
    
    def check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """Check IP reputation using external services"""
        if ip_address in self.ip_reputation_cache:
            return self.ip_reputation_cache[ip_address]
        
        reputation = {
            'score': 0.0,
            'threat_level': 'low',
            'categories': [],
            'last_updated': timezone.now()
        }
        
        try:
            # Check if IP is private/local
            if ipaddress.ip_address(ip_address).is_private:
                reputation['score'] = 0.0
                reputation['threat_level'] = 'low'
                reputation['categories'].append('private_ip')
            else:
                # Check with abuseipdb (if configured)
                if hasattr(settings, 'ABUSEIPDB_API_KEY'):
                    reputation = self._check_abuseipdb(ip_address)
                
                # Check with IPQualityScore (if configured)
                elif hasattr(settings, 'IPQUALITYSCORE_API_KEY'):
                    reputation = self._check_ipqualityscore(ip_address)
                
                # Basic GeoIP check
                if self.geoip_reader:
                    try:
                        response = self.geoip_reader.city(ip_address)
                        if response.country.iso_code in ['CN', 'RU', 'KP']:  # High-risk countries
                            reputation['score'] += 0.3
                            reputation['categories'].append('high_risk_country')
                    except geoip2.errors.AddressNotFoundError:
                        pass
        
        except Exception as e:
            logger.error(f"Error checking IP reputation for {ip_address}: {e}")
        
        # Cache result
        self.ip_reputation_cache[ip_address] = reputation
        cache.set(f'ip_reputation:{ip_address}', reputation, timeout=3600)
        
        return reputation
    
    def _check_abuseipdb(self, ip_address: str) -> Dict[str, Any]:
        """Check IP with AbuseIPDB"""
        try:
            url = f"https://api.abuseipdb.com/api/v2/check"
            headers = {
                'Accept': 'application/json',
                'Key': settings.ABUSEIPDB_API_KEY
            }
            params = {
                'ipAddress': ip_address,
                'maxAgeInDays': '90'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get('data'):
                abuse_confidence = data['data'].get('abuseConfidenceScore', 0)
                categories = data['data'].get('reports', [])
                
                return {
                    'score': abuse_confidence / 100.0,
                    'threat_level': 'high' if abuse_confidence > 50 else 'medium' if abuse_confidence > 20 else 'low',
                    'categories': [cat['category'] for cat in categories],
                    'last_updated': timezone.now()
                }
        
        except Exception as e:
            logger.error(f"Error checking AbuseIPDB for {ip_address}: {e}")
        
        return {
            'score': 0.0,
            'threat_level': 'low',
            'categories': [],
            'last_updated': timezone.now()
        }
    
    def _check_ipqualityscore(self, ip_address: str) -> Dict[str, Any]:
        """Check IP with IPQualityScore"""
        try:
            url = f"https://ipqualityscore.com/api/json/ip/{settings.IPQUALITYSCORE_API_KEY}/{ip_address}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if response.status_code == 200:
                fraud_score = data.get('fraud_score', 0)
                proxy = data.get('proxy', False)
                vpn = data.get('vpn', False)
                tor = data.get('tor', False)
                
                categories = []
                if proxy:
                    categories.append('proxy')
                if vpn:
                    categories.append('vpn')
                if tor:
                    categories.append('tor')
                
                return {
                    'score': fraud_score / 100.0,
                    'threat_level': 'high' if fraud_score > 75 else 'medium' if fraud_score > 50 else 'low',
                    'categories': categories,
                    'last_updated': timezone.now()
                }
        
        except Exception as e:
            logger.error(f"Error checking IPQualityScore for {ip_address}: {e}")
        
        return {
            'score': 0.0,
            'threat_level': 'low',
            'categories': [],
            'last_updated': timezone.now()
        }
    
    def analyze_request(self, request: HttpRequest) -> Dict[str, Any]:
        """Comprehensive request analysis"""
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        analysis = {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'risk_score': 0.0,
            'threat_indicators': [],
            'recommendations': []
        }
        
        # Check if IP is blocked
        if self.is_ip_blocked(ip_address):
            analysis['risk_score'] = 1.0
            analysis['threat_indicators'].append('blocked_ip')
            analysis['recommendations'].append('Block request immediately')
            return analysis
        
        # Check IP reputation
        reputation = self.check_ip_reputation(ip_address)
        if reputation['score'] > 0.7:
            analysis['risk_score'] += 0.4
            analysis['threat_indicators'].append('high_reputation_risk')
            analysis['recommendations'].append('Consider blocking IP')
        elif reputation['score'] > 0.3:
            analysis['risk_score'] += 0.2
            analysis['threat_indicators'].append('medium_reputation_risk')
        
        # Check suspicious patterns
        suspicious_patterns = self.check_suspicious_patterns(request)
        if suspicious_patterns:
            analysis['risk_score'] += 0.3
            analysis['threat_indicators'].append('suspicious_patterns')
            analysis['recommendations'].append('Investigate request content')
        
        # Check rate limiting
        rate_limit_ok, rate_limit_info = self.check_rate_limit(request)
        if not rate_limit_ok:
            analysis['risk_score'] += 0.2
            analysis['threat_indicators'].append('rate_limit_exceeded')
            analysis['recommendations'].append('Apply rate limiting')
        
        # Check for unusual activity patterns
        if self._is_unusual_activity(ip_address, request):
            analysis['risk_score'] += 0.2
            analysis['threat_indicators'].append('unusual_activity')
            analysis['recommendations'].append('Monitor for additional suspicious activity')
        
        return analysis
    
    def _is_unusual_activity(self, ip_address: str, request: HttpRequest) -> bool:
        """Check for unusual activity patterns"""
        # Get recent activity for this IP
        recent_events = [event for event in self.security_events 
                        if event.ip_address == ip_address and 
                        event.timestamp > timezone.now() - timedelta(hours=1)]
        
        if len(recent_events) > 100:  # More than 100 events in last hour
            return True
        
        # Check for rapid-fire requests
        recent_timestamps = [event.timestamp for event in recent_events]
        if len(recent_timestamps) > 10:
            time_diffs = [(recent_timestamps[i] - recent_timestamps[i-1]).total_seconds() 
                         for i in range(1, len(recent_timestamps))]
            if any(diff < 1.0 for diff in time_diffs):  # Requests less than 1 second apart
                return True
        
        return False
    
    def log_security_event(self, event_type: str, severity: str, ip_address: str,
                          user_agent: str, request_path: str, user_id: Optional[int],
                          details: Dict[str, Any]):
        """Log a security event"""
        event = SecurityEvent(
            timestamp=timezone.now(),
            event_type=event_type,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request_path,
            user_id=user_id,
            details=details
        )
        
        self.security_events.append(event)
        
        # Store in cache for monitoring
        cache_key = f'security_event:{ip_address}:{int(time.time())}'
        cache.set(cache_key, {
            'event_type': event_type,
            'severity': severity,
            'details': details
        }, timeout=86400)
        
        # Log to file
        logger.warning(f"Security Event: {event_type} - {severity} - IP: {ip_address} - Path: {request_path}")
        
        # Update threat indicators
        self._update_threat_indicators(event)
    
    def _update_threat_indicators(self, event: SecurityEvent):
        """Update threat indicators based on security events"""
        if event.ip_address not in self.threat_indicators:
            self.threat_indicators[event.ip_address] = ThreatIndicator(
                ip_address=event.ip_address,
                threat_type=event.event_type,
                confidence=0.1,
                first_seen=event.timestamp,
                last_seen=event.timestamp,
                event_count=1,
                details={}
            )
        else:
            indicator = self.threat_indicators[event.ip_address]
            indicator.event_count += 1
            indicator.last_seen = event.timestamp
            
            # Increase confidence based on event frequency and severity
            if event.severity == 'high':
                indicator.confidence += 0.2
            elif event.severity == 'medium':
                indicator.confidence += 0.1
            else:
                indicator.confidence += 0.05
            
            # Cap confidence at 1.0
            indicator.confidence = min(indicator.confidence, 1.0)
    
    def get_security_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate security report for specified time period"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        recent_events = [event for event in self.security_events 
                        if event.timestamp >= cutoff_time]
        
        # Group events by type
        event_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        ip_counts = defaultdict(int)
        
        for event in recent_events:
            event_counts[event.event_type] += 1
            severity_counts[event.severity] += 1
            ip_counts[event.ip_address] += 1
        
        # Get top threat indicators
        top_threats = sorted(
            self.threat_indicators.values(),
            key=lambda x: x.confidence,
            reverse=True
        )[:10]
        
        return {
            'period_hours': hours,
            'total_events': len(recent_events),
            'event_counts': dict(event_counts),
            'severity_counts': dict(severity_counts),
            'top_ips': dict(sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_threats': [
                {
                    'ip_address': threat.ip_address,
                    'threat_type': threat.threat_type,
                    'confidence': threat.confidence,
                    'event_count': threat.event_count,
                    'first_seen': threat.first_seen.isoformat(),
                    'last_seen': threat.last_seen.isoformat()
                }
                for threat in top_threats
            ],
            'blocked_ips_count': len(self.blocked_ips)
        }

# Global security system instance
advanced_security = AdvancedSecuritySystem() 