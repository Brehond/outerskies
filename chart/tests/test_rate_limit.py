from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.core.cache import cache
from chart.middleware.rate_limit import RateLimitMiddleware
import time

class RateLimitMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = RateLimitMiddleware(get_response=lambda r: HttpResponse())
        cache.clear()  # Clear cache before each test

    def test_default_rate_limit(self):
        """Test that default rate limit is enforced."""
        # Make requests up to the limit
        for _ in range(100):  # Default limit is 100
            request = self.factory.get('/some/path/')
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Next request should be rate limited
        request = self.factory.get('/some/path/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)  # Too Many Requests

    def test_api_rate_limit(self):
        """Test that API endpoints have stricter rate limits."""
        # Make requests up to the API limit
        for _ in range(50):  # API limit is 50
            request = self.factory.get('/api/chart/')
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Next request should be rate limited
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)

    def test_auth_rate_limit(self):
        """Test that auth endpoints have the strictest rate limits."""
        # Make requests up to the auth limit
        for _ in range(20):  # Auth limit is 20
            request = self.factory.get('/auth/login/')
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

        # Next request should be rate limited
        request = self.factory.get('/auth/login/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)

    def test_rate_limit_headers(self):
        """Test that rate limit headers are set correctly."""
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        
        self.assertIn('X-RateLimit-Limit', response)
        self.assertIn('X-RateLimit-Remaining', response)
        self.assertIn('X-RateLimit-Reset', response)
        
        self.assertEqual(response['X-RateLimit-Limit'], '50')  # API limit
        self.assertEqual(response['X-RateLimit-Remaining'], '49')  # 50 - 1

    def test_rate_limit_reset(self):
        """Test that rate limits reset after the time window."""
        # Make requests up to the limit
        for _ in range(50):
            request = self.factory.get('/api/chart/')
            self.middleware(request)

        # Should be rate limited
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)

        # Wait for rate limit window to expire
        time.sleep(61)  # Window is 60 seconds

        # Should work again
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_static_file_exemption(self):
        """Test that static files are exempt from rate limiting."""
        # Make many requests to a static file
        for _ in range(200):  # More than any rate limit
            request = self.factory.get('/static/css/style.css')
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200)

    def test_different_methods(self):
        """Test that different HTTP methods have separate rate limits."""
        # Make requests up to the limit with GET
        for _ in range(50):
            request = self.factory.get('/api/chart/')
            self.middleware(request)

        # GET should be rate limited
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429)

        # POST should still work
        request = self.factory.post('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200) 