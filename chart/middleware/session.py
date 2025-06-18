import time
import logging
from django.conf import settings
from django.http import HttpResponseForbidden
from django.core.cache import cache
from django.contrib.sessions.backends.base import SessionBase
from django.utils.crypto import constant_time_compare, get_random_string

logger = logging.getLogger('security')

class SessionSecurityMiddleware:
    """
    Session security middleware that provides:
    - Session fixation protection
    - Session hijacking prevention
    - Session timeout
    - Session rotation
    - Session validation
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.session_timeout = getattr(settings, 'SESSION_COOKIE_AGE', 3600)  # 1 hour
        self.session_rotation = getattr(settings, 'SESSION_ROTATION', 300)  # 5 minutes
        self.max_failed_attempts = getattr(settings, 'MAX_SESSION_ATTEMPTS', 5)
        self.lockout_time = getattr(settings, 'SESSION_LOCKOUT_TIME', 900)  # 15 minutes
        
    def __call__(self, request):
        if not hasattr(request, 'session'):
            return self.get_response(request)
            
        # Check session validity
        if not self._is_valid_session(request):
            return self._handle_invalid_session(request)
            
        # Check session timeout
        if self._is_session_expired(request):
            return self._handle_expired_session(request)
            
        # Check session rotation
        if self._should_rotate_session(request):
            self._rotate_session(request)
            
        # Check for session fixation
        if self._is_session_fixation_attempt(request):
            return self._handle_session_fixation(request)
            
        # Check for session hijacking
        if self._is_session_hijacking_attempt(request):
            return self._handle_session_hijacking(request)
            
        response = self.get_response(request)
        
        # Add security headers
        self._add_session_security_headers(response)
        
        return response
        
    def _is_valid_session(self, request):
        """Check if session is valid."""
        if not request.session.session_key:
            return False
            
        # Check if session exists in cache
        if not cache.get(f'session:{request.session.session_key}'):
            return False
            
        # Check if session is locked
        if cache.get(f'session_locked:{request.session.session_key}'):
            return False
            
        return True
        
    def _is_session_expired(self, request):
        """Check if session has expired."""
        if not request.session.get('last_activity'):
            return True
            
        last_activity = request.session.get('last_activity')
        return time.time() - last_activity > self.session_timeout
        
    def _should_rotate_session(self, request):
        """Check if session should be rotated."""
        if not request.session.get('last_rotation'):
            return True
            
        last_rotation = request.session.get('last_rotation')
        return time.time() - last_rotation > self.session_rotation
        
    def _is_session_fixation_attempt(self, request):
        """Check for session fixation attempts."""
        if not request.session.get('session_id'):
            return False
            
        # Check if session ID matches expected pattern
        if not self._is_valid_session_id(request.session.get('session_id')):
            return True
            
        # Check if session ID has changed unexpectedly
        if request.session.get('session_id') != request.session.session_key:
            return True
            
        return False
        
    def _is_session_hijacking_attempt(self, request):
        """Check for session hijacking attempts."""
        if not request.session.get('user_agent'):
            return False
            
        # Check if user agent has changed
        if request.session.get('user_agent') != request.META.get('HTTP_USER_AGENT'):
            return True
            
        # Check if IP has changed
        if request.session.get('ip_address') != self._get_client_ip(request):
            return True
            
        return False
        
    def _handle_invalid_session(self, request):
        """Handle invalid session."""
        logger.warning(f'Invalid session attempt from {self._get_client_ip(request)}')
        request.session.flush()
        return HttpResponseForbidden('Invalid session')
        
    def _handle_expired_session(self, request):
        """Handle expired session."""
        logger.info(f'Session expired for {self._get_client_ip(request)}')
        request.session.flush()
        return HttpResponseForbidden('Session expired')
        
    def _handle_session_fixation(self, request):
        """Handle session fixation attempt."""
        logger.warning(f'Session fixation attempt from {self._get_client_ip(request)}')
        request.session.flush()
        return HttpResponseForbidden('Invalid session')
        
    def _handle_session_hijacking(self, request):
        """Handle session hijacking attempt."""
        logger.warning(f'Session hijacking attempt from {self._get_client_ip(request)}')
        request.session.flush()
        return HttpResponseForbidden('Invalid session')
        
    def _rotate_session(self, request):
        """Rotate session ID."""
        old_session_key = request.session.session_key
        request.session.cycle_key()
        request.session['last_rotation'] = time.time()
        
        # Update cache
        cache.delete(f'session:{old_session_key}')
        cache.set(f'session:{request.session.session_key}', True, self.session_timeout)
        
    def _add_session_security_headers(self, response):
        """Add session security headers."""
        response['X-Session-Timeout'] = str(self.session_timeout)
        response['X-Session-Rotation'] = str(self.session_rotation)
        
    def _is_valid_session_id(self, session_id):
        """Check if session ID is valid."""
        if not session_id:
            return False
            
        # Check length
        if len(session_id) != 32:
            return False
            
        # Check if it's alphanumeric
        if not session_id.isalnum():
            return False
            
        return True
        
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR') 