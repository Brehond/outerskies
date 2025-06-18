from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from chart.middleware.auth import APIAuthMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from datetime import datetime, timedelta
import json

class APIAuthMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = APIAuthMiddleware(get_response=lambda r: HttpResponse())
        
        # Create a test JWT token
        self.token = AccessToken()
        self.token['exp'] = int((datetime.now() + timedelta(hours=1)).timestamp())
        self.valid_token = str(self.token)
        
        # Create an expired token
        self.expired_token = AccessToken()
        self.expired_token['exp'] = int((datetime.now() - timedelta(hours=1)).timestamp())
        self.expired_token = str(self.expired_token)

    def test_no_auth_for_static_files(self):
        """Test that static files don't require authentication."""
        request = self.factory.get('/static/css/style.css')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_no_auth_for_non_api_endpoints(self):
        """Test that non-API endpoints don't require authentication."""
        request = self.factory.get('/some/path/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_no_auth_provided(self):
        """Test that API endpoints require authentication."""
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Authentication required')

    def test_valid_jwt_token(self):
        """Test that valid JWT tokens are accepted."""
        request = self.factory.get(
            '/api/chart/',
            HTTP_AUTHORIZATION=f'Bearer {self.valid_token}'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.auth_method, 'jwt')
        self.assertEqual(request.auth_token, f'Bearer {self.valid_token}')

    def test_expired_jwt_token(self):
        """Test that expired JWT tokens are rejected."""
        request = self.factory.get(
            '/api/chart/',
            HTTP_AUTHORIZATION=f'Bearer {self.expired_token}'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid or expired token')

    def test_valid_api_key(self):
        """Test that valid API keys are accepted."""
        request = self.factory.get(
            '/api/chart/',
            HTTP_X_API_KEY='test_key_1'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.auth_method, 'api_key')
        self.assertEqual(request.api_key, 'test_key_1')

    def test_invalid_api_key(self):
        """Test that invalid API keys are rejected."""
        request = self.factory.get(
            '/api/chart/',
            HTTP_X_API_KEY='invalid_key'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid or expired API key')

    def test_api_key_path_restriction(self):
        """Test that API keys are restricted to allowed paths."""
        request = self.factory.get(
            '/api/restricted/',
            HTTP_X_API_KEY='test_key_1'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid or expired API key')

    def test_api_key_expiration(self):
        """Test that expired API keys are rejected."""
        # Create a key that expires in the past
        self.middleware.api_keys['expired_key'] = {
            'name': 'Expired Key',
            'expires': datetime.now() - timedelta(days=1),
            'allowed_paths': ['/api/chart/']
        }
        
        request = self.factory.get(
            '/api/chart/',
            HTTP_X_API_KEY='expired_key'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid or expired API key') 