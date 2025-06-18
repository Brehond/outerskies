import re
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

logger = logging.getLogger('security')

class PasswordSecurityMiddleware:
    """
    Password security middleware that handles:
    - Password complexity validation
    - Password expiration
    - Password history
    - Password rotation
    - Brute force protection
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Password policy settings
        self.min_length = getattr(settings, 'PASSWORD_MIN_LENGTH', 12)
        self.require_uppercase = getattr(settings, 'PASSWORD_REQUIRE_UPPERCASE', True)
        self.require_lowercase = getattr(settings, 'PASSWORD_REQUIRE_LOWERCASE', True)
        self.require_numbers = getattr(settings, 'PASSWORD_REQUIRE_NUMBERS', True)
        self.require_special = getattr(settings, 'PASSWORD_REQUIRE_SPECIAL', True)
        self.max_age = getattr(settings, 'PASSWORD_MAX_AGE', 90)  # days
        self.history_size = getattr(settings, 'PASSWORD_HISTORY_SIZE', 5)
        self.max_attempts = getattr(settings, 'PASSWORD_MAX_ATTEMPTS', 5)
        self.lockout_time = getattr(settings, 'PASSWORD_LOCKOUT_TIME', 15)  # minutes
        
        # Password patterns
        self.patterns = {
            'uppercase': re.compile(r'[A-Z]'),
            'lowercase': re.compile(r'[a-z]'),
            'numbers': re.compile(r'[0-9]'),
            'special': re.compile(r'[!@#$%^&*(),.?":{}|<>]')
        }
        
    def __call__(self, request):
        # Only process password-related endpoints
        if not self._is_password_endpoint(request):
            return self.get_response(request)
            
        # Check for brute force attempts
        if self._is_brute_force_attempt(request):
            return JsonResponse({
                'error': 'Too many failed attempts. Please try again later.'
            }, status=429)
            
        # Process the request
        response = self.get_response(request)
        
        # If this was a password change, update history
        if self._is_password_change(request, response):
            self._update_password_history(request)
            
        return response
        
    def _is_password_endpoint(self, request):
        """Check if the request is for a password-related endpoint."""
        return request.path in {
            '/api/auth/password/change/',
            '/api/auth/password/reset/',
            '/api/auth/password/verify/'
        }
        
    def _is_brute_force_attempt(self, request):
        """Check if there have been too many failed attempts."""
        if request.method != 'POST':
            return False
            
        client_ip = self._get_client_ip(request)
        key = f'password_attempts_{client_ip}'
        attempts = cache.get(key, 0)
        
        if attempts >= self.max_attempts:
            return True
            
        cache.set(key, attempts + 1, self.lockout_time * 60)
        return False
        
    def _is_password_change(self, request, response):
        """Check if this was a successful password change."""
        return (
            request.method == 'POST' and
            request.path == '/api/auth/password/change/' and
            response.status_code == 200
        )
        
    def _update_password_history(self, request):
        """Update password history for the user."""
        try:
            user = request.user
            password = request.POST.get('new_password')
            
            if not user or not password:
                return
                
            # Get current history
            history = cache.get(f'password_history_{user.id}', [])
            
            # Add new password hash
            history.append(password)
            
            # Keep only the last N passwords
            if len(history) > self.history_size:
                history = history[-self.history_size:]
                
            # Update history
            cache.set(f'password_history_{user.id}', history)
            
            # Update last change time
            cache.set(f'password_last_change_{user.id}', datetime.now())
            
        except Exception as e:
            logger.error(f'Error updating password history: {str(e)}')
            
    def validate_password(self, password, user=None):
        """Validate password against security policies."""
        errors = []
        
        # Check length
        if len(password) < self.min_length:
            errors.append(f'Password must be at least {self.min_length} characters long')
            
        # Check complexity
        if self.require_uppercase and not self.patterns['uppercase'].search(password):
            errors.append('Password must contain at least one uppercase letter')
            
        if self.require_lowercase and not self.patterns['lowercase'].search(password):
            errors.append('Password must contain at least one lowercase letter')
            
        if self.require_numbers and not self.patterns['numbers'].search(password):
            errors.append('Password must contain at least one number')
            
        if self.require_special and not self.patterns['special'].search(password):
            errors.append('Password must contain at least one special character')
            
        # Check history
        if user:
            history = cache.get(f'password_history_{user.id}', [])
            if password in history:
                errors.append('Password cannot be reused')
                
        # Check expiration
        if user:
            last_change = cache.get(f'password_last_change_{user.id}')
            if last_change and (datetime.now() - last_change).days > self.max_age:
                errors.append('Password has expired')
                
        # Use Django's password validation
        try:
            validate_password(password, user)
        except ValidationError as e:
            errors.extend(e.messages)
            
        return errors
        
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')
        
    def get_password_status(self, user):
        """Get password status information."""
        last_change = cache.get(f'password_last_change_{user.id}')
        days_remaining = None
        
        if last_change:
            days_remaining = self.max_age - (datetime.now() - last_change).days
            
        return {
            'last_change': last_change,
            'days_remaining': days_remaining,
            'is_expired': days_remaining is not None and days_remaining <= 0
        } 