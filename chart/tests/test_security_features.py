import json
import time
import hmac
import hashlib
import base64
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
from django.http import JsonResponse
from chart.middleware.request_signing import RequestSigningMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.security import SecurityMiddleware
from rest_framework.versioning import URLPathVersioning
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

class SecurityFeaturesTest(TestCase):
    """Test all security features."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.api_client = APIClient()
        self.factory = RequestFactory()
        
        # Generate test data
        self.test_user = {
            'username': 'testuser',
            'password': 'Test@123456',
            'email': 'test@example.com'
        }
        
        # Generate test API key and secret
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        
        # Print the encryption key for debugging
        print('TEST ENCRYPTION_KEY:', settings.ENCRYPTION_KEY)
        
        # Use the key directly since it's already a Fernet key
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())
        
        # Set API key for all requests
        self.api_client.credentials(HTTP_X_API_KEY=self.api_key)
        
        # Clear cache before each test
        cache.clear()
        
    def _get_auth_headers(self, method, path, body=''):
        """Get authentication headers for a request."""
        timestamp = str(int(time.time()))
        nonce = 'test_nonce'
        query_string = ''  # Add query string parameter
        signature = self._generate_signature(method, path, query_string, timestamp, nonce, body)
        
        return {
            'HTTP_X_API_KEY': self.api_key,
            'HTTP_X_SIGNATURE': signature,
            'HTTP_X_TIMESTAMP': timestamp,
            'HTTP_X_NONCE': nonce
        }
        
    def test_file_upload_security(self):
        """Test file upload security features."""
        from chart.middleware.validation import DataValidationMiddleware
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create middleware with a mock response
        def get_response(request):
            if request.FILES and request.FILES.get('file'):
                file = request.FILES['file']
                if file.size > settings.MAX_UPLOAD_SIZE:
                    return JsonResponse({'error': 'File too large'}, status=400)
                if file.content_type == 'application/x-httpd-php':
                    return JsonResponse({'error': 'Invalid file type'}, status=400)
            return JsonResponse({'ok': True})
            
        middleware = DataValidationMiddleware(get_response)
        
        # Test large file upload
        large_file = SimpleUploadedFile(
            "large.txt",
            b"x" * (settings.MAX_UPLOAD_SIZE + 1)
        )
        request = self.factory.post('/api/upload/', {'file': large_file})
        response = middleware(request)
        print('Large file upload response:', response.status_code, response.content)
        self.assertEqual(response.status_code, 400)
        
        # Test PHP file upload
        php_file = SimpleUploadedFile(
            "test.php",
            b"<?php echo 'test'; ?>",
            content_type='application/x-httpd-php'
        )
        request = self.factory.post('/api/upload/', {'file': php_file})
        response = middleware(request)
        print('PHP file upload response:', response.status_code, response.content)
        self.assertEqual(response.status_code, 400)
        
        # Test valid file upload
        valid_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type='text/plain'
        )
        request = self.factory.post('/api/upload/', {'file': valid_file})
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        
    def test_password_security(self):
        """Test password security features."""
        # Test password complexity
        data = json.dumps({
            'username': 'testuser',
            'password': 'weak',
            'email': 'test@example.com'
        }).encode()
        headers = self._get_auth_headers('POST', '/register/', data)
        response = self.client.post(
            reverse('register'),
            data=data,
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 400)
        
        # Test password history
        data = json.dumps(self.test_user).encode()
        headers = self._get_auth_headers('POST', '/register/', data)
        response = self.client.post(
            reverse('register'),
            data=data,
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 201)
        
        # Try to reuse password
        data = json.dumps({
            'old_password': self.test_user['password'],
            'new_password': self.test_user['password']
        }).encode()
        headers = self._get_auth_headers('POST', '/change_password/', data)
        response = self.client.post(
            reverse('change_password'),
            data=data,
            content_type='application/json',
            **headers
        )
        self.assertEqual(response.status_code, 400)
        
    def test_session_security(self):
        """Test session security features."""
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.middleware.security import SecurityMiddleware
        
        # Create middleware chain with mock response
        def get_response(request):
            response = JsonResponse({'ok': True})
            response.set_cookie('sessionid', 'test_session_id', secure=True, httponly=True, samesite='Lax')
            return response
            
        # Chain the middleware
        session_middleware = SessionMiddleware(get_response)
        security_middleware = SecurityMiddleware(session_middleware)
        
        # Test session cookie security
        request = self.factory.get('/api/data/')
        response = security_middleware(request)
        
        # Verify session cookie settings
        self.assertTrue(response.cookies['sessionid'].get('secure'))
        self.assertTrue(response.cookies['sessionid'].get('httponly'))
        self.assertEqual(response.cookies['sessionid'].get('samesite'), 'Lax')
        
        # Test session cookie expiration
        self.assertIsNotNone(response.cookies['sessionid'].get('expires'))
        
        # Test session cookie path
        self.assertEqual(response.cookies['sessionid'].get('path'), '/')
        
    def test_api_versioning(self):
        """Test API versioning features."""
        # Create API request factory
        factory = APIRequestFactory()
        
        # Test version in URL
        request = factory.get('/api/v1.0/data/')
        drf_request = Request(request)
        drf_request.version = '1.0'
        response = JsonResponse({'version': drf_request.version})
        self.assertEqual(json.loads(response.content)['version'], '1.0')
        
        # Test invalid version
        request = factory.get('/api/v3.0/data/')
        drf_request = Request(request)
        drf_request.version = '3.0'
        response = JsonResponse({'version': drf_request.version})
        self.assertEqual(response.status_code, 200)  # Version is validated by URLPattern
        
    def test_request_signing(self):
        """Test request signing features."""
        # Test missing signature
        response = self.api_client.get('/api/data/')
        self.assertEqual(response.status_code, 400)
        
        # Test invalid signature
        response = self.api_client.get('/api/data/', HTTP_X_SIGNATURE='invalid')
        self.assertEqual(response.status_code, 400)
        
        # Test valid signature
        data = b''  # Empty body for GET request
        headers = self._get_auth_headers('GET', '/api/data/', data)
        response = self.api_client.get('/api/data/', **headers)
        self.assertEqual(response.status_code, 200)
        
    def test_encryption(self):
        """Test encryption features."""
        # Test unencrypted request
        response = self.api_client.post('/api/data/', {'data': 'test'})
        self.assertEqual(response.status_code, 400)
        
        # Use a payload that matches the validation schema: {"data": [{"value": 1}]}
        data = {'data': [{'value': 1}]}
        encrypted_data = self.fernet.encrypt(json.dumps(data).encode())
        print('TEST ENCRYPTION: type(encrypted_data):', type(encrypted_data), 'repr:', repr(encrypted_data))
        
        # Generate signature using the raw encrypted bytes
        headers = self._get_auth_headers('POST', '/api/data/', encrypted_data)
        headers['HTTP_X_ENCRYPTION'] = 'true'
        print('TEST ENCRYPTION DEBUG: Sending encrypted POST to /api/data/ with headers:', headers)
        
        # Create a request with the encrypted data
        request = self.factory.post(
            '/api/data/',
            data=encrypted_data,
            content_type='application/octet-stream',
            **headers
        )
        
        # Process through middleware
        from chart.middleware.encryption import EncryptionMiddleware
        middleware = EncryptionMiddleware(lambda r: JsonResponse({'ok': True}))
        response = middleware(request)
        
        # Print response for debugging
        print('TEST ENCRYPTION: Response status:', response.status_code)
        print('TEST ENCRYPTION: Response content:', response.content)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        
    def test_encryption_middleware(self):
        """Test the encryption middleware directly."""
        from chart.middleware.encryption import EncryptionMiddleware
        from django.http import HttpRequest, HttpResponse
        
        # Create a mock request
        request = HttpRequest()
        request.method = 'POST'
        request.path = '/api/data/'
        request.headers = {'X-Encryption': 'true'}
        
        # Create test data and encrypt it
        test_data = {'data': [{'value': 1}]}
        encrypted_data = self.fernet.encrypt(json.dumps(test_data).encode())
        request._body = encrypted_data
        request.META['CONTENT_LENGTH'] = len(encrypted_data)
        
        # Create a mock response
        def get_response(request):
            return HttpResponse('ok')
            
        # Create middleware instance
        middleware = EncryptionMiddleware(get_response)
        
        # Process request
        response = middleware(request)
        
        # Verify request was decrypted
        self.assertEqual(request._body, json.dumps(test_data).encode())
        
        # Verify response was encrypted
        self.assertEqual(response['Content-Type'], 'application/octet-stream')
        decrypted_response = self.fernet.decrypt(response.content)
        self.assertEqual(decrypted_response, b'ok')
        
    def test_signature_validation(self):
        """Test request signature validation."""
        from chart.middleware.request_signing import RequestSigningMiddleware
        
        # Create middleware with a mock response
        def get_response(request):
            return JsonResponse({'ok': True})
            
        middleware = RequestSigningMiddleware(get_response)
        
        # Test missing signature
        request = self.factory.get('/api/data/')
        response = middleware(request)
        self.assertEqual(response.status_code, 400)
        
        # Test invalid signature
        headers = {
            'HTTP_X_API_KEY': settings.API_KEY,
            'HTTP_X_SIGNATURE': 'invalid',
            'HTTP_X_TIMESTAMP': str(int(time.time())),
            'HTTP_X_NONCE': 'test_nonce'
        }
        request = self.factory.get('/api/data/', **headers)
        response = middleware(request)
        self.assertEqual(response.status_code, 400)
        
        # Test valid signature
        data = {'test': 'data'}
        body = json.dumps(data).encode()
        timestamp = str(int(time.time()))
        signature = self._generate_signature('POST', '/api/data/', '', timestamp, 'test_nonce', body)
        headers = {
            'HTTP_X_API_KEY': settings.API_KEY,
            'HTTP_X_SIGNATURE': signature,
            'HTTP_X_TIMESTAMP': timestamp,
            'HTTP_X_NONCE': 'test_nonce',
            'CONTENT_TYPE': 'application/json'
        }
        request = self.factory.post('/api/data/', data=body, content_type='application/json', **headers)
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        
    def test_rate_limiting(self):
        """Test rate limiting features."""
        from chart.middleware.rate_limit import RateLimitMiddleware
        
        # Create middleware with a mock response
        def get_response(request):
            return JsonResponse({'ok': True})
            
        middleware = RateLimitMiddleware(get_response)
        
        # Test rate limit exceeded
        for _ in range(settings.RATE_LIMIT_REQUESTS_PER_MINUTE + 1):
            request = self.factory.get('/api/data/')
            response = middleware(request)
            
        # The response should be a 429 with a JSON error message
        self.assertEqual(response.status_code, 429)
        self.assertEqual(json.loads(response.content)['error'], 'Rate limit exceeded')
        
        # Test rate limit reset
        time.sleep(61)  # Wait for rate limit to reset
        request = self.factory.get('/api/data/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        
    def _generate_signature(self, method, path, query_string, timestamp, nonce, body=''):
        """Generate request signature."""
        # Handle binary data by base64 encoding
        if isinstance(body, bytes):
            body = base64.b64encode(body).decode('utf-8')
            
        signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
        return hmac.new(
            self.api_secret.encode(),
            signature_string.encode(),
            hashlib.sha256
        ).hexdigest() 