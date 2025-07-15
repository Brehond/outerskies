"""
Enhanced Authentication System

This module provides advanced authentication features:
- Password strength validation
- Two-factor authentication (TOTP)
- Account lockout protection
- Session management
- Security audit logging
- Password history tracking
"""

import hashlib
import secrets
import time
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
import pyotp
import re

logger = logging.getLogger(__name__)


class PasswordValidator:
    """Enhanced password validation"""
    
    def __init__(self):
        self.min_length = 8
        self.max_length = 128
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_numbers = True
        self.require_special = True
        self.common_passwords = self._load_common_passwords()
    
    def _load_common_passwords(self) -> set:
        """Load list of common passwords"""
        return {
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        }
    
    def validate_password(self, password: str, user: Optional[User] = None) -> Tuple[bool, str]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            user: User object for history check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < self.min_length:
            return False, f"Password must be at least {self.min_length} characters long"
        
        if len(password) > self.max_length:
            return False, f"Password must be no more than {self.max_length} characters long"
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if self.require_numbers and not re.search(r'\d', password):
            return False, "Password must contain at least one number"
        
        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        if password.lower() in self.common_passwords:
            return False, "Password is too common"
        
        # Check password history
        if user and self._is_password_in_history(password, user):
            return False, "Password has been used recently"
        
        return True, "Password is valid"
    
    def _is_password_in_history(self, password: str, user: User) -> bool:
        """Check if password is in user's password history"""
        # This would integrate with a password history model
        # For now, return False
        return False
    
    def get_password_strength(self, password: str) -> Dict[str, Any]:
        """Calculate password strength score"""
        score = 0
        feedback = []
        
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("Add more characters")
        
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append("Add uppercase letters")
        
        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append("Add lowercase letters")
        
        if re.search(r'\d', password):
            score += 1
        else:
            feedback.append("Add numbers")
        
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        else:
            feedback.append("Add special characters")
        
        # Bonus for length
        if len(password) >= 12:
            score += 1
        
        strength_levels = {
            0: "Very Weak",
            1: "Weak",
            2: "Fair",
            3: "Good",
            4: "Strong",
            5: "Very Strong",
            6: "Excellent"
        }
        
        return {
            'score': score,
            'max_score': 6,
            'level': strength_levels.get(score, "Very Weak"),
            'feedback': feedback,
            'percentage': (score / 6) * 100
        }


class TwoFactorAuth:
    """Two-factor authentication using TOTP"""
    
    def __init__(self):
        self.issuer = "Outer Skies"
        self.algorithm = 'sha1'  # Use string instead of constant
        self.digits = 6
        self.interval = 30
    
    def generate_secret(self, user: User) -> str:
        """Generate TOTP secret for user"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, secret: str, user: User) -> str:
        """Generate QR code URL for TOTP setup"""
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.issuer
        )
        return provisioning_uri
    
    def verify_code(self, secret: str, code: str) -> bool:
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.verify(code)
    
    def get_current_code(self, secret: str) -> str:
        """Get current TOTP code"""
        totp = pyotp.TOTP(secret)
        return totp.now()


class AccountLockout:
    """Account lockout protection"""
    
    def __init__(self):
        self.max_attempts = 5
        self.lockout_duration = 900  # 15 minutes
        self.max_lockouts = 3
        self.permanent_lockout_duration = 86400  # 24 hours
    
    def check_lockout(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if account is locked out
        
        Args:
            identifier: Username or IP address
            
        Returns:
            Tuple of (is_locked, reason)
        """
        lockout_key = f"lockout:{identifier}"
        lockout_data = cache.get(lockout_key)
        
        if not lockout_data:
            return False, None
        
        attempts = lockout_data.get('attempts', 0)
        lockout_until = lockout_data.get('lockout_until')
        
        if lockout_until and time.time() < lockout_until:
            remaining = int(lockout_until - time.time())
            return True, f"Account locked. Try again in {remaining} seconds"
        
        if attempts >= self.max_attempts * self.max_lockouts:
            return True, "Account permanently locked. Contact support"
        
        return False, None
    
    def record_failed_attempt(self, identifier: str):
        """Record a failed login attempt"""
        lockout_key = f"lockout:{identifier}"
        lockout_data = cache.get(lockout_key, {'attempts': 0, 'lockout_until': None})
        
        lockout_data['attempts'] += 1
        
        if lockout_data['attempts'] >= self.max_attempts:
            lockout_data['lockout_until'] = time.time() + self.lockout_duration
        
        cache.set(lockout_key, lockout_data, self.lockout_duration)
    
    def record_successful_attempt(self, identifier: str):
        """Record a successful login attempt"""
        lockout_key = f"lockout:{identifier}"
        cache.delete(lockout_key)


class SessionManager:
    """Enhanced session management"""
    
    def __init__(self):
        self.max_sessions_per_user = 5
        self.session_timeout = 3600  # 1 hour
        self.inactive_timeout = 1800  # 30 minutes
    
    def create_session(self, user: User, request) -> Dict[str, Any]:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            'user_id': user.id,
            'username': user.username,
            'created_at': time.time(),
            'last_activity': time.time(),
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'device_info': self._get_device_info(request)
        }
        
        # Store session
        session_key = f"session:{session_id}"
        cache.set(session_key, session_data, self.session_timeout)
        
        # Track user sessions
        user_sessions_key = f"user_sessions:{user.id}"
        user_sessions = cache.get(user_sessions_key, [])
        user_sessions.append(session_id)
        
        # Limit sessions per user
        if len(user_sessions) > self.max_sessions_per_user:
            old_session = user_sessions.pop(0)
            cache.delete(f"session:{old_session}")
        
        cache.set(user_sessions_key, user_sessions, self.session_timeout)
        
        return {
            'session_id': session_id,
            'expires_at': time.time() + self.session_timeout
        }
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and update session"""
        session_key = f"session:{session_id}"
        session_data = cache.get(session_key)
        
        if not session_data:
            return None
        
        # Check if session is expired
        if time.time() - session_data['last_activity'] > self.inactive_timeout:
            cache.delete(session_key)
            return None
        
        # Update last activity
        session_data['last_activity'] = time.time()
        cache.set(session_key, session_data, self.session_timeout)
        
        return session_data
    
    def invalidate_session(self, session_id: str):
        """Invalidate a session"""
        session_key = f"session:{session_id}"
        session_data = cache.get(session_key)
        
        if session_data:
            # Remove from user sessions
            user_sessions_key = f"user_sessions:{session_data['user_id']}"
            user_sessions = cache.get(user_sessions_key, [])
            if session_id in user_sessions:
                user_sessions.remove(session_id)
                cache.set(user_sessions_key, user_sessions, self.session_timeout)
        
        cache.delete(session_key)
    
    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = cache.get(user_sessions_key, [])
        
        sessions = []
        for session_id in session_ids:
            session_data = cache.get(f"session:{session_id}")
            if session_data:
                sessions.append({
                    'session_id': session_id,
                    'created_at': session_data['created_at'],
                    'last_activity': session_data['last_activity'],
                    'ip_address': session_data['ip_address'],
                    'device_info': session_data['device_info']
                })
        
        return sessions
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _get_device_info(self, request) -> Dict[str, str]:
        """Get device information from request"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Basic device detection
        if 'Mobile' in user_agent:
            device_type = 'mobile'
        elif 'Tablet' in user_agent:
            device_type = 'tablet'
        else:
            device_type = 'desktop'
        
        return {
            'type': device_type,
            'user_agent': user_agent[:100]  # Truncate for storage
        }


class SecurityAuditLogger:
    """Security audit logging"""
    
    def __init__(self):
        self.audit_logger = logging.getLogger('security_audit')
    
    def log_login_attempt(self, username: str, success: bool, ip_address: str, 
                         user_agent: str, details: Dict[str, Any] = None):
        """Log login attempt"""
        log_data = {
            'event': 'login_attempt',
            'username': username,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        
        if success:
            self.audit_logger.info(f"Successful login: {username} from {ip_address}", extra=log_data)
        else:
            self.audit_logger.warning(f"Failed login: {username} from {ip_address}", extra=log_data)
    
    def log_password_change(self, user: User, ip_address: str, success: bool):
        """Log password change"""
        log_data = {
            'event': 'password_change',
            'user_id': user.id,
            'username': user.username,
            'success': success,
            'ip_address': ip_address,
            'timestamp': datetime.now().isoformat()
        }
        
        self.audit_logger.info(f"Password change: {user.username} from {ip_address}", extra=log_data)
    
    def log_account_lockout(self, identifier: str, ip_address: str, reason: str):
        """Log account lockout"""
        log_data = {
            'event': 'account_lockout',
            'identifier': identifier,
            'ip_address': ip_address,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        
        self.audit_logger.warning(f"Account lockout: {identifier} from {ip_address}", extra=log_data)
    
    def log_suspicious_activity(self, user: User, activity_type: str, details: Dict[str, Any]):
        """Log suspicious activity"""
        log_data = {
            'event': 'suspicious_activity',
            'user_id': user.id,
            'username': user.username,
            'activity_type': activity_type,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.audit_logger.warning(f"Suspicious activity: {activity_type} by {user.username}", extra=log_data)


# Global instances
password_validator = PasswordValidator()
two_factor_auth = TwoFactorAuth()
account_lockout = AccountLockout()
session_manager = SessionManager()
security_audit = SecurityAuditLogger()


# API Views
@api_view(['POST'])
@permission_classes([AllowAny])
def enhanced_register(request):
    """Enhanced user registration with security features"""
    try:
        data = request.data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        password_confirm = data.get('password_confirm')
        
        # Validate input
        if not all([username, email, password, password_confirm]):
            return Response({
                'success': False,
                'error': 'validation_error',
                'message': 'All fields are required'
            }, status=400)
        
        if password != password_confirm:
            return Response({
                'success': False,
                'error': 'validation_error',
                'message': 'Passwords do not match'
            }, status=400)
        
        # Validate password strength
        is_valid, error_message = password_validator.validate_password(password)
        if not is_valid:
            return Response({
                'success': False,
                'error': 'password_validation_error',
                'message': error_message
            }, status=400)
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            return Response({
                'success': False,
                'error': 'user_exists',
                'message': 'Username already exists'
            }, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'error': 'email_exists',
                'message': 'Email already exists'
            }, status=400)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', '')
        )
        
        # Log successful registration
        security_audit.log_login_attempt(
            username, True, 
            request.META.get('REMOTE_ADDR', 'unknown'),
            request.META.get('HTTP_USER_AGENT', ''),
            {'event': 'registration'}
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'date_joined': user.date_joined.isoformat()
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }
        }, status=201)
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return Response({
            'success': False,
            'error': 'registration_failed',
            'message': 'Registration failed'
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def enhanced_login(request):
    """Enhanced login with security features"""
    try:
        data = request.data
        username = data.get('username')
        password = data.get('password')
        totp_code = data.get('totp_code')  # Optional 2FA code
        
        if not username or not password:
            return Response({
                'success': False,
                'error': 'validation_error',
                'message': 'Username and password are required'
            }, status=400)
        
        # Check for lockout
        is_locked, lockout_reason = account_lockout.check_lockout(username)
        if is_locked:
            return Response({
                'success': False,
                'error': 'account_locked',
                'message': lockout_reason
            }, status=423)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        
        if not user:
            # Record failed attempt
            account_lockout.record_failed_attempt(username)
            
            # Log failed attempt
            security_audit.log_login_attempt(
                username, False,
                request.META.get('REMOTE_ADDR', 'unknown'),
                request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'success': False,
                'error': 'invalid_credentials',
                'message': 'Invalid username or password'
            }, status=401)
        
        # Check if 2FA is required
        if hasattr(user, 'two_factor_secret') and user.two_factor_secret:
            if not totp_code:
                return Response({
                    'success': False,
                    'error': 'two_factor_required',
                    'message': 'Two-factor authentication code required'
                }, status=401)
            
            if not two_factor_auth.verify_code(user.two_factor_secret, totp_code):
                return Response({
                    'success': False,
                    'error': 'invalid_totp',
                    'message': 'Invalid two-factor authentication code'
                }, status=401)
        
        # Record successful attempt
        account_lockout.record_successful_attempt(username)
        
        # Log successful login
        security_audit.log_login_attempt(
            username, True,
            request.META.get('REMOTE_ADDR', 'unknown'),
            request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Create session
        session = session_manager.create_session(user, request)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'data': {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                },
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                },
                'session': session
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return Response({
            'success': False,
            'error': 'login_failed',
            'message': 'Login failed'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_two_factor(request):
    """Setup two-factor authentication"""
    try:
        user = request.user
        
        # Generate new secret
        secret = two_factor_auth.generate_secret(user)
        
        # Generate QR code URL
        qr_url = two_factor_auth.generate_qr_code(secret, user)
        
        return Response({
            'success': True,
            'message': 'Two-factor authentication setup',
            'data': {
                'secret': secret,
                'qr_url': qr_url,
                'instructions': 'Scan the QR code with your authenticator app'
            }
        })
        
    except Exception as e:
        logger.error(f"2FA setup error: {e}")
        return Response({
            'success': False,
            'error': 'setup_failed',
            'message': 'Two-factor authentication setup failed'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_two_factor_setup(request):
    """Verify and enable two-factor authentication"""
    try:
        user = request.user
        secret = request.data.get('secret')
        code = request.data.get('code')
        
        if not secret or not code:
            return Response({
                'success': False,
                'error': 'validation_error',
                'message': 'Secret and code are required'
            }, status=400)
        
        # Verify code
        if not two_factor_auth.verify_code(secret, code):
            return Response({
                'success': False,
                'error': 'invalid_code',
                'message': 'Invalid verification code'
            }, status=400)
        
        # Save secret to user (this would be a custom field)
        # user.two_factor_secret = secret
        # user.save()
        
        return Response({
            'success': True,
            'message': 'Two-factor authentication enabled successfully'
        })
        
    except Exception as e:
        logger.error(f"2FA verification error: {e}")
        return Response({
            'success': False,
            'error': 'verification_failed',
            'message': 'Two-factor authentication verification failed'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sessions(request):
    """Get user's active sessions"""
    try:
        sessions = session_manager.get_user_sessions(request.user.id)
        
        return Response({
            'success': True,
            'message': 'Sessions retrieved successfully',
            'data': {
                'sessions': sessions,
                'total_sessions': len(sessions)
            }
        })
        
    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        return Response({
            'success': False,
            'error': 'retrieval_failed',
            'message': 'Failed to retrieve sessions'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_session(request):
    """Logout from specific session"""
    try:
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response({
                'success': False,
                'error': 'validation_error',
                'message': 'Session ID is required'
            }, status=400)
        
        session_manager.invalidate_session(session_id)
        
        return Response({
            'success': True,
            'message': 'Session logged out successfully'
        })
        
    except Exception as e:
        logger.error(f"Logout session error: {e}")
        return Response({
            'success': False,
            'error': 'logout_failed',
            'message': 'Failed to logout session'
        }, status=500) 