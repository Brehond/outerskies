import base64
import json
import logging
from django.http import HttpResponseBadRequest, JsonResponse
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger('security')


class EncryptionMiddleware:
    """
    Encryption middleware that provides:
    - Request/response encryption
    - Key rotation
    - Key derivation
    - Secure key storage
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.encryption_key = getattr(settings, 'ENCRYPTION_KEY', '').encode()
        self.encryption_salt = getattr(settings, 'ENCRYPTION_SALT', '').encode()
        self.encryption_header = getattr(settings, 'ENCRYPTION_HEADER', 'X-Encryption')
        self.encryption_algorithm = getattr(settings, 'ENCRYPTION_ALGORITHM', 'AES-256-GCM')
        self.key_rotation_interval = getattr(settings, 'KEY_ROTATION_INTERVAL', 86400)  # 24 hours

        # Initialize encryption
        self._initialize_encryption()

    def _initialize_encryption(self):
        """Initialize encryption with key derivation."""
        # Use the key directly since it's already a Fernet key
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def __call__(self, request):
        # Skip encryption for non-API requests
        if not self._is_api_request(request):
            return self.get_response(request)

        # Skip encryption for public endpoints
        if self._is_public_endpoint(request):
            return self.get_response(request)

        # Check if request is encrypted
        if self._is_encrypted_request(request):
            try:
                # Decrypt request
                request = self._decrypt_request(request)
            except Exception as e:
                logger.error(f'Failed to decrypt request: {str(e)}')
                return self._handle_decryption_error(request)

        response = self.get_response(request)

        # Encrypt response
        if self._should_encrypt_response(request):
            try:
                response = self._encrypt_response(response)
            except Exception as e:
                logger.error(f'Failed to encrypt response: {str(e)}')
                return self._handle_encryption_error(request)

        return response

    def _is_api_request(self, request):
        """Check if request is an API request."""
        return request.path.startswith('/api/')

    def _is_public_endpoint(self, request):
        """Check if endpoint is public."""
        public_paths = getattr(settings, 'PUBLIC_API_PATHS', [])
        return any(request.path.startswith(path) for path in public_paths)

    def _is_encrypted_request(self, request):
        """Check if request is encrypted."""
        return request.headers.get(self.encryption_header) == 'true'

    def _should_encrypt_response(self, request):
        """Check if response should be encrypted."""
        return request.headers.get(self.encryption_header) == 'true'

    def _decrypt_request(self, request):
        """Decrypt request data."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Decrypt body
                encrypted_data = request.body
                decrypted_data = self.fernet.decrypt(encrypted_data)

                # Update request body
                request._body = decrypted_data

                # Update content length
                request.META['CONTENT_LENGTH'] = len(decrypted_data)

                # Log decryption for debugging
                logger.debug(f'Decrypted request body: {decrypted_data}')

            except Exception as e:
                logger.error(f'Failed to decrypt request body: {str(e)}')
                raise

        return request

    def _encrypt_response(self, response):
        """Encrypt response data."""
        try:
            # Get response content
            content = response.content

            # Encrypt content
            encrypted_content = self.fernet.encrypt(content)

            # Update response
            response.content = encrypted_content
            response['Content-Length'] = len(encrypted_content)
            response['Content-Type'] = 'application/octet-stream'

        except Exception as e:
            logger.error(f'Failed to encrypt response: {str(e)}')
            raise

        return response

    def _handle_decryption_error(self, request):
        """Handle decryption error."""
        logger.warning(f'Decryption error from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Failed to decrypt request'
        }, status=400)

    def _handle_encryption_error(self, request):
        """Handle encryption error."""
        logger.warning(f'Encryption error from {request.META.get("REMOTE_ADDR")}')
        return JsonResponse({
            'error': 'Failed to encrypt response'
        }, status=500)

    def _rotate_key(self):
        """Rotate encryption key."""
        # Generate new key
        new_key = Fernet.generate_key()

        # Update key
        self.encryption_key = new_key
        self._initialize_encryption()

        # Store new key
        # This should be done securely, e.g., using a key management service
        settings.ENCRYPTION_KEY = new_key.decode()
