from django.test import TestCase, Client, RequestFactory
from django.http import HttpResponse
from django.urls import reverse
from django.test.utils import override_settings
import unittest
from chart.middleware.security import EnhancedSecurityMiddleware
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.middleware.csrf import get_token, CsrfViewMiddleware
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from chart.tests.test_urls import dummy_chart_view

class EnhancedSecurityMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client(enforce_csrf_checks=True)  # Enable CSRF checks
        self.middleware = EnhancedSecurityMiddleware(get_response=lambda r: HttpResponse())

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        # Test GET request with SQL injection attempt
        response = self.client.get('/api/chart/', {'query': "'; DROP TABLE users; --"})
        self.assertEqual(response.status_code, 403)

        # Test POST request with SQL injection attempt
        response = self.client.post('/api/chart/', {'query': "'; DROP TABLE users; --"})
        self.assertEqual(response.status_code, 403)

    def test_xss_prevention(self):
        """Test XSS prevention."""
        # Test GET request with XSS attempt
        response = self.client.get('/api/chart/', {'query': '<script>alert("xss")</script>'})
        self.assertEqual(response.status_code, 403)

        # Test POST request with XSS attempt
        response = self.client.post('/api/chart/', {'query': '<script>alert("xss")</script>'})
        self.assertEqual(response.status_code, 403)

    def test_security_headers(self):
        """Test security headers are set correctly."""
        response = self.client.get('/api/chart/')
        
        # Check security headers
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.get('X-Frame-Options'), 'DENY')
        self.assertEqual(response.get('X-XSS-Protection'), '1; mode=block')
        self.assertEqual(response.get('Strict-Transport-Security'), 'max-age=31536000; includeSubDomains')
        self.assertIsNotNone(response.get('Content-Security-Policy'))

    def test_session_security(self):
        """Test session security settings."""
        response = self.client.get('/api/chart/')
        
        # Check session cookie settings
        session_cookie = response.cookies.get(settings.SESSION_COOKIE_NAME)
        self.assertIsNotNone(session_cookie)
        self.assertTrue(session_cookie.get('httponly'))
        self.assertEqual(session_cookie.get('samesite'), 'Lax')
        self.assertTrue(session_cookie.get('secure'))

    def test_csrf_protection(self):
        """Test CSRF protection."""
        # Test POST without CSRF token (should be blocked)
        response = self.client.post('/api/chart/')
        self.assertEqual(response.status_code, 403)  # Should be blocked

        # Test POST with CSRF token (should succeed)
        response = self.client.get('/api/chart/')  # Get CSRF token
        csrf_token = response.cookies['csrftoken'].value
        response = self.client.post('/api/chart/', HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 200)  # Should succeed

    def test_csp_header(self):
        """Test Content Security Policy header."""
        response = self.client.get('/api/chart/')
        csp_header = response.get('Content-Security-Policy')
        
        # Check CSP directives
        self.assertIn("default-src 'self'", csp_header)
        self.assertIn("script-src 'self'", csp_header)
        self.assertIn("style-src 'self'", csp_header)
        self.assertIn("font-src 'self'", csp_header)
        self.assertIn("img-src 'self'", csp_header)
        self.assertIn("connect-src 'self'", csp_header)

    def test_static_file_exemption(self):
        """Test that static files are exempt from security checks."""
        response = self.client.get('/static/css/style.css')
        self.assertNotEqual(response.status_code, 403)

    def test_media_file_exemption(self):
        """Test that media files are exempt from security checks."""
        response = self.client.get('/media/uploads/test.jpg')
        self.assertNotEqual(response.status_code, 403)

    def test_sql_injection_patterns(self):
        """Test various SQL injection patterns."""
        patterns = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users; --",
            "'; EXEC xp_cmdshell('net user'); --",
            "' OR 1=1; --",
        ]
        
        for pattern in patterns:
            response = self.client.get('/api/chart/', {'query': pattern})
            self.assertEqual(response.status_code, 403)

    def test_xss_patterns(self):
        """Test various XSS patterns."""
        patterns = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            'vbscript:alert("xss")',
            'onload=alert("xss")',
            'onerror=alert("xss")',
        ]
        
        for pattern in patterns:
            response = self.client.get('/api/chart/', {'query': pattern})
            self.assertEqual(response.status_code, 403)

    def test_session_expiry(self):
        """Test session expiry settings."""
        # Set session expiry to 0 for non-HTTPS
        request = self.factory.get('/api/chart/')
        # Attach a session to the request
        session_middleware = SessionMiddleware(lambda req: HttpResponse())
        session_middleware.process_request(request)
        request.session.save()
        response = self.middleware.process_response(request, HttpResponse())
        # Check session expiry
        self.assertEqual(request.session.get_expiry_age(), 3600)  # Expect 1 hour

    def test_secure_cookie_settings(self):
        """Test secure cookie settings."""
        # Make a GET request to get the CSRF cookie
        response = self.client.get('/api/chart/', HTTP_HOST='testserver', secure=True)
        print('DEBUG COOKIES:', response.cookies)  # Debug output
        # Check CSRF cookie settings
        csrf_cookie = response.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertIsNotNone(csrf_cookie)
        self.assertTrue(csrf_cookie.get('secure'))
        self.assertEqual(csrf_cookie.get('samesite'), 'Lax')
        self.assertTrue(csrf_cookie.get('httponly'))

    def test_request_size_validation(self):
        """Test that requests exceeding the maximum size are rejected."""
        # Create a large request
        large_data = 'x' * (1024 * 1024 + 1)  # 1MB + 1 byte
        request = self.factory.post('/api/chart/', data={'data': large_data})
        request.META['CONTENT_LENGTH'] = str(len(large_data))
        
        # Process the request
        response = self.middleware(request)
        self.assertEqual(response.status_code, 413)  # Payload Too Large

    def test_request_size_validation_get(self):
        """Test that GET requests are not subject to size validation."""
        # Create a large GET request
        large_data = 'x' * (1024 * 1024 + 1)  # 1MB + 1 byte
        request = self.factory.get('/api/chart/', data={'data': large_data})
        request.META['CONTENT_LENGTH'] = str(len(large_data))
        
        # Process the request
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)  # Should pass

    def test_request_size_validation_small(self):
        """Test that requests under the maximum size are accepted."""
        # Create a small request
        small_data = 'x' * (1024 * 512)  # 512KB
        request = self.factory.post('/api/chart/', data={'data': small_data})
        request.META['CONTENT_LENGTH'] = str(len(small_data))
        
        # Process the request
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)  # Should pass 