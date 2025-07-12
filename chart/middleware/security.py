import re
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings
import logging
from django.contrib.sessions.middleware import SessionMiddleware

logger = logging.getLogger('security')


class EnhancedSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced security middleware that provides:
    - XSS protection
    - SQL injection prevention
    - Secure session handling
    - Additional security headers
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        # Maximum request size in bytes (1MB)
        self.max_request_size = getattr(settings, 'MAX_REQUEST_SIZE', 1024 * 1024)

        # SQL injection patterns
        self.sql_patterns = [
            re.compile(r"(\%27)|(\')|(\-\-)|(\%23)|(#)", re.IGNORECASE),  # SQL comments
            re.compile(r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))", re.IGNORECASE),  # SQL injection
            re.compile(r"((\%27)|(\'))union", re.IGNORECASE),  # SQL UNION
            re.compile(r"exec(\s|\+)+(s|x)p\w+", re.IGNORECASE),  # SQL stored procedures
            re.compile(r"((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))", re.IGNORECASE),  # SQL OR
            re.compile(r"((\%27)|(\'))((\%61)|a|(\%41))((\%6E)|n|(\%4E))((\%64)|d|(\%44))", re.IGNORECASE),  # SQL AND
            re.compile(r"((\%27)|(\'))((\%69)|i|(\%49))((\%6E)|n|(\%4E))((\%73)|s|(\%53))((\%65)|e|(\%45))((\%72)|r|(\%52))", re.IGNORECASE),  # SQL INSERT
            re.compile(r"((\%27)|(\'))((\%64)|d|(\%44))((\%72)|r|(\%52))((\%6F)|o|(\%4F))((\%70)|p|(\%50))", re.IGNORECASE),  # SQL DROP
            re.compile(r"((\%27)|(\'))((\%75)|u|(\%55))((\%70)|p|(\%50))((\%64)|d|(\%44))((\%61)|a|(\%41))((\%74)|t|(\%54))((\%65)|e|(\%45))", re.IGNORECASE),  # SQL UPDATE
            re.compile(r"((\%27)|(\'))((\%64)|d|(\%44))((\%65)|e|(\%45))((\%6C)|l|(\%4C))((\%65)|e|(\%45))((\%74)|t|(\%54))((\%65)|e|(\%45))", re.IGNORECASE),  # SQL DELETE
        ]

        # XSS patterns
        self.xss_patterns = [
            re.compile(r"<script[^>]*>[\s\S]*?</script>", re.IGNORECASE),  # Basic script tag
            re.compile(r"javascript:", re.IGNORECASE),  # JavaScript protocol
            re.compile(r"on\w+\s*=", re.IGNORECASE),  # Event handlers
            re.compile(r"expression\s*\(", re.IGNORECASE),  # CSS expressions
            re.compile(r"eval\s*\(", re.IGNORECASE),  # JavaScript eval
            re.compile(r"document\.cookie", re.IGNORECASE),  # Cookie access
            re.compile(r"document\.write", re.IGNORECASE),  # Document write
            re.compile(r"alert\s*\(", re.IGNORECASE),  # Alert function
            re.compile(r"confirm\s*\(", re.IGNORECASE),  # Confirm function
            re.compile(r"prompt\s*\(", re.IGNORECASE),  # Prompt function
        ]

        self.session_middleware = SessionMiddleware(get_response)

    def __call__(self, request):
        # Skip for static/media files
        if request.path.startswith(('/static/', '/media/')):
            return self.get_response(request)

        # Process request through session middleware
        response = self.session_middleware(request)

        # Regenerate session ID if it exists
        if hasattr(request, 'session') and request.session.session_key:
            request.session.cycle_key()

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = f'max-age={settings.SECURE_HSTS_SECONDS}; includeSubDomains; preload'

        # Set secure cookie settings
        if 'sessionid' in response.cookies:
            response.cookies['sessionid']['secure'] = True
            response.cookies['sessionid']['httponly'] = True
            response.cookies['sessionid']['samesite'] = 'Lax'

        if 'csrftoken' in response.cookies:
            response.cookies['csrftoken']['secure'] = True
            response.cookies['csrftoken']['httponly'] = True
            response.cookies['csrftoken']['samesite'] = 'Lax'

        return response

    def process_request(self, request):
        """Process the request and check for security violations."""
        # Skip security checks for static files only
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None

        # Check request size
        if self._check_request_size(request):
            return HttpResponse('Request too large', status=413)  # Payload Too Large

        # Check for SQL injection attempts
        if self._check_sql_injection(request):
            logger.warning(f'SQL injection attempt detected from {request.META.get("REMOTE_ADDR")}')
            return HttpResponseForbidden('Forbidden')

        # Check for XSS attempts
        if self._check_xss(request):
            logger.warning(f'XSS attempt detected from {request.META.get("REMOTE_ADDR")}')
            return HttpResponseForbidden('Forbidden')

        return None

    def process_response(self, request, response):
        """Add security headers to the response."""
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Secure session handling
        if hasattr(request, 'session'):
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            if not request.is_secure():
                request.session.set_expiry(0)  # Expire session on non-HTTPS

        return response

    def _check_sql_injection(self, request):
        """Check for SQL injection attempts in request data."""
        # Check GET parameters
        for key, value in request.GET.items():
            if any(pattern.search(value) for pattern in self.sql_patterns):
                logger.warning(f'SQL injection attempt detected from {request.META.get("REMOTE_ADDR")}')
                return True

        # Check POST parameters
        if request.method == 'POST':
            for key, value in request.POST.items():
                if any(pattern.search(value) for pattern in self.sql_patterns):
                    logger.warning(f'SQL injection attempt detected from {request.META.get("REMOTE_ADDR")}')
                    return True

        return False

    def _check_xss(self, request):
        """Check for XSS attempts in request data."""
        # Check GET parameters
        for key, value in request.GET.items():
            if any(pattern.search(value) for pattern in self.xss_patterns):
                logger.warning(f'XSS attempt detected from {request.META.get("REMOTE_ADDR")}')
                return True

        # Check POST parameters
        if request.method == 'POST':
            for key, value in request.POST.items():
                if any(pattern.search(value) for pattern in self.xss_patterns):
                    logger.warning(f'XSS attempt detected from {request.META.get("REMOTE_ADDR")}')
                    return True

        return False

    def _check_request_size(self, request):
        """Check if the request size exceeds the maximum allowed size."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_length = request.META.get('CONTENT_LENGTH', 0)
            try:
                content_length = int(content_length)
                if content_length > self.max_request_size:
                    logger.warning(f'Request too large ({content_length} bytes) from {request.META.get("REMOTE_ADDR")}')
                    return True
            except (ValueError, TypeError):
                pass
        return False
