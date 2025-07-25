import hmac
import hashlib
import time
import logging
from django.http import HttpResponseForbidden, JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.utils.crypto import constant_time_compare

logger = logging.getLogger('security')


class RequestSigningMiddleware:
    """
    Request signing middleware that provides:
    - Request signature validation
    - Timestamp validation
    - Nonce validation
    - Replay attack prevention
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.api_key = getattr(settings, 'API_KEY', '')
        self.api_secret = getattr(settings, 'API_SECRET', '')
        self.signature_header = getattr(settings, 'SIGNATURE_HEADER', 'X-Signature')
        self.timestamp_header = getattr(settings, 'TIMESTAMP_HEADER', 'X-Timestamp')
        self.nonce_header = getattr(settings, 'NONCE_HEADER', 'X-Nonce')
        self.timestamp_window = getattr(settings, 'TIMESTAMP_WINDOW', 300)  # 5 minutes
        self.nonce_expiry = getattr(settings, 'NONCE_EXPIRY', 3600)  # 1 hour

    def __call__(self, request):
        # Skip signing for non-API requests
        if not self._is_api_request(request):
            return self.get_response(request)

        # Skip signing for public endpoints
        if self._is_public_endpoint(request):
            return self.get_response(request)

        # Get request signature
        signature = request.headers.get(self.signature_header)
        if not signature:
            return self._handle_missing_signature(request)

        # Get timestamp
        timestamp = request.headers.get(self.timestamp_header)
        if not timestamp:
            return self._handle_missing_timestamp(request)

        # Get nonce
        nonce = request.headers.get(self.nonce_header)
        if not nonce:
            return self._handle_missing_nonce(request)

        # Validate timestamp
        if not self._is_valid_timestamp(timestamp):
            return self._handle_invalid_timestamp(request, timestamp)

        # Validate nonce
        if not self._is_valid_nonce(nonce):
            return self._handle_invalid_nonce(request, nonce)

        # Validate signature
        if not self._is_valid_signature(request, signature, timestamp, nonce):
            return self._handle_invalid_signature(request)

        response = self.get_response(request)

        # Add security headers
        self._add_security_headers(response)

        return response

    def _is_api_request(self, request):
        """Check if request is an API request."""
        return request.path.startswith('/api/')

    def _is_public_endpoint(self, request):
        """Check if endpoint is public and should skip signature validation."""
        public_paths = [
            '/api/health/',
            '/api/public/',
            '/api/docs/',
            '/api/v1/docs/',
            '/api/v1/security/',
            '/api/v1/rate-limits/',
            '/api/v1/status/',
            '/api/v1/error-codes/',
            '/api/v1/code-examples/',
            '/api/v1/system/health/',
            '/api/v1/system/ai_models/',
            '/api/v1/system/themes/',
            '/api/v1/auth/register/',
            '/api/v1/auth/login/',
            '/api/v1/auth/refresh/',
            '/api/v1/auth/logout/',
        ]

        # Skip signature validation for public endpoints
        if any(request.path.startswith(path) for path in public_paths):
            return True

        # Skip signature validation for protected endpoints that use JWT authentication
        protected_paths = [
            '/api/v1/users/',
            '/api/v1/charts/',
            '/api/v1/subscriptions/',
            '/api/v1/payments/',
            '/api/v1/coupons/',
            '/api/v1/chat/',
        ]

        # If it's a protected endpoint and has JWT token, skip signature
        if any(request.path.startswith(path) for path in protected_paths):
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                return True

        return False

    def _is_valid_timestamp(self, timestamp):
        """Check if timestamp is valid."""
        try:
            timestamp = int(timestamp)
            current_time = int(time.time())
            return abs(current_time - timestamp) <= self.timestamp_window
        except (ValueError, TypeError):
            return False

    def _is_valid_nonce(self, nonce):
        """Check if nonce is valid."""
        try:
            # Check if nonce exists in cache
            if cache.get(f'nonce:{nonce}'):
                return False

            # Store nonce in cache
            cache.set(f'nonce:{nonce}', True, self.nonce_expiry)
            return True
        except Exception as e:
            # If cache fails, log warning but allow the request (fail open)
            logger.warning(f"Nonce cache operation failed: {e}")
            return True

    def _is_valid_signature(self, request, signature, timestamp, nonce):
        """Check if signature is valid."""
        # Get request data
        method = request.method
        path = request.path
        query_string = request.META.get('QUERY_STRING', '')

        # Handle binary data by base64 encoding
        if request.body:
            import base64
            body = base64.b64encode(request.body).decode('utf-8')
        else:
            body = ''

        # Build signature string
        signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'

        # Calculate expected signature
        expected_signature = hmac.new(
            self.api_secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Debug logging
        logger.warning(f"SIGNATURE DEBUG for {method} {path}:")
        logger.warning(f"  Received signature: {signature}")
        logger.warning(f"  Expected signature: {expected_signature}")
        logger.warning(f"  Timestamp: {timestamp}")
        logger.warning(f"  Nonce: {nonce}")
        logger.warning(f"  Body length: {len(request.body)}")
        logger.warning(f"  Body base64: {body[:100]}..." if body else "  Body: empty")
        logger.warning(f"  Signature string: {repr(signature_string)}")

        return constant_time_compare(signature, expected_signature)

    def _get_request_body(self, request):
        """Get request body."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            return request.body.decode('utf-8', errors='replace')
        return ''

    def _handle_missing_signature(self, request):
        """Handle missing signature."""
        logger.warning(f'Missing signature from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Request signature is required'
        }, status=400)

    def _handle_missing_timestamp(self, request):
        """Handle missing timestamp."""
        logger.warning(f'Missing timestamp from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Request timestamp is required'
        }, status=400)

    def _handle_missing_nonce(self, request):
        """Handle missing nonce."""
        logger.warning(f'Missing nonce from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Request nonce is required'
        }, status=400)

    def _handle_invalid_timestamp(self, request, timestamp):
        """Handle invalid timestamp."""
        logger.warning(f'Invalid timestamp {timestamp} from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Invalid request timestamp',
            'window': self.timestamp_window
        }, status=400)

    def _handle_invalid_nonce(self, request, nonce):
        """Handle invalid nonce."""
        logger.warning(f'Invalid nonce {nonce} from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Invalid request nonce'
        }, status=400)

    def _handle_invalid_signature(self, request):
        """Handle invalid signature."""
        logger.warning(f'Invalid signature from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Invalid request signature'
        }, status=400)

    def _add_security_headers(self, response):
        """Add security headers."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
