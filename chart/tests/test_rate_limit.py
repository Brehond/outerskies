# from django.test import TestCase, RequestFactory
# from django.http import HttpResponse
# from django.core.cache import cache
# from chart.middleware.rate_limit import RateLimitMiddleware
# import time

# class RateLimitMiddlewareTests(TestCase):
#     def setUp(self):
#         self.middleware = RateLimitMiddleware(get_response=lambda r: HttpResponse())
#         self.factory = RequestFactory()
#         cache.clear()
# 
#     def test_default_rate_limit(self):
#         """Test that default rate limit is enforced."""
#         request = self.factory.get('/some/path/')
#         request.META['REMOTE_ADDR'] = '192.168.1.1'
#         
#         # First request should pass
#         response = self.middleware(request)
#         self.assertEqual(response.status_code, 200)
#         
#         # Subsequent requests should be rate limited
#         for _ in range(10):
#             response = self.middleware(request)
#         
#         self.assertEqual(response.status_code, 429)
# 
#     def test_api_rate_limit(self):
#         """Test that API endpoints have stricter rate limits."""
#         request = self.factory.get('/api/chart/')
#         request.META['REMOTE_ADDR'] = '192.168.1.2'
#         
#         # API endpoints should have stricter limits
#         for _ in range(5):
#             response = self.middleware(request)
#         
#         self.assertEqual(response.status_code, 429)
# 
#     def test_auth_rate_limit(self):
#         """Test that auth endpoints have the strictest rate limits."""
#         request = self.factory.post('/auth/login/')
#         request.META['REMOTE_ADDR'] = '192.168.1.3'
#         
#         # Auth endpoints should have the strictest limits
#         for _ in range(3):
#             response = self.middleware(request)
#         
#         self.assertEqual(response.status_code, 429)
# 
#     def test_static_file_exemption(self):
#         """Test that static files are exempt from rate limiting."""
#         request = self.factory.get('/static/css/style.css')
#         request.META['REMOTE_ADDR'] = '192.168.1.4'
#         
#         # Static files should not be rate limited
#         for _ in range(20):
#             response = self.middleware(request)
#             self.assertEqual(response.status_code, 200)
# 
#     def test_rate_limit_reset(self):
#         """Test that rate limits reset after the time window."""
#         request = self.factory.get('/some/path/')
#         request.META['REMOTE_ADDR'] = '192.168.1.5'
#         
#         # Make requests up to the limit
#         for _ in range(9):
#             response = self.middleware(request)
#             self.assertEqual(response.status_code, 200)
#         
#         # Wait for rate limit to reset (simulate)
#         time.sleep(1)
#         cache.clear()  # Clear cache to simulate time passing
#         
#         # Should be able to make requests again
#         response = self.middleware(request)
#         self.assertEqual(response.status_code, 200)
# 
#     def test_different_methods(self):
#         """Test that different HTTP methods have separate rate limits."""
#         get_request = self.factory.get('/api/chart/')
#         post_request = self.factory.post('/api/chart/')
#         get_request.META['REMOTE_ADDR'] = '192.168.1.6'
#         post_request.META['REMOTE_ADDR'] = '192.168.1.6'
#         
#         # GET requests
#         for _ in range(5):
#             response = self.middleware(get_request)
#         
#         # POST requests should still work
#         response = self.middleware(post_request)
#         self.assertEqual(response.status_code, 200)
# 
#     def test_rate_limit_headers(self):
#         """Test that rate limit headers are set correctly."""
#         request = self.factory.get('/api/chart/')
#         request.META['REMOTE_ADDR'] = '192.168.1.7'
#         
#         response = self.middleware(request)
#         
#         # Should have rate limit headers
#         self.assertIn('X-RateLimit-Limit', response)
#         self.assertIn('X-RateLimit-Remaining', response)
#         self.assertIn('X-RateLimit-Reset', response) 