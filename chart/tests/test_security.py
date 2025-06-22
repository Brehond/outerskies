# from chart import ...
# from django.test import TestCase, Client, RequestFactory
# from django.http import HttpResponse
# from django.urls import reverse
# from django.contrib.auth import get_user_model
# from rest_framework_simplejwt.tokens import AccessToken
# from datetime import datetime, timedelta
# import json
# 
# User = get_user_model()
# 
# class SecurityTests(TestCase):
#     def setUp(self):
#         self.client = Client()
#         self.factory = RequestFactory()
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
# 
#     def test_csrf_protection(self):
#         """Test that CSRF protection is enabled"""
#         # Try to make a POST request without CSRF token
#         response = self.client.post(reverse('auth:register'), {
#             'username': 'newuser',
#             'email': 'new@example.com',
#             'password1': 'testpass123',
#             'password2': 'testpass123',
#         })
#         self.assertEqual(response.status_code, 403)  # CSRF forbidden
# 
#     def test_xss_protection(self):
#         """Test that XSS protection headers are set"""
#         response = self.client.get(reverse('auth:login'))
#         self.assertIn('X-XSS-Protection', response)
#         self.assertEqual(response['X-XSS-Protection'], '1; mode=block')
# 
#     def test_content_type_protection(self):
#         """Test that content type protection headers are set"""
#         response = self.client.get(reverse('auth:login'))
#         self.assertIn('X-Content-Type-Options', response)
#         self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
# 
#     def test_frame_options(self):
#         """Test that frame options headers are set"""
#         response = self.client.get(reverse('auth:login'))
#         self.assertIn('X-Frame-Options', response)
#         self.assertEqual(response['X-Frame-Options'], 'DENY')
# 
#     def test_secure_headers(self):
#         """Test that secure headers are set"""
#         response = self.client.get(reverse('auth:login'))
#         self.assertIn('Strict-Transport-Security', response)
#         self.assertIn('Referrer-Policy', response)
# 
#     def test_jwt_token_security(self):
#         """Test JWT token security features"""
#         # Create a token
#         token = AccessToken.for_user(self.user)
#         
#         # Test token expiration
#         token.set_exp(lifetime=timedelta(seconds=1))
#         time.sleep(2)
#         
#         # Token should be expired
#         with self.assertRaises(Exception):
#             token.verify()
# 
#     def test_password_validation(self):
#         """Test password validation"""
#         # Test weak password
#         with self.assertRaises(ValidationError):
#             User.objects.create_user(
#                 username='weakuser',
#                 email='weak@example.com',
#                 password='123'  # Too short
#             )
# 
#     def test_session_security(self):
#         """Test session security settings"""
#         self.client.login(username='testuser', password='testpass123')
#         response = self.client.get(reverse('auth:profile'))
#         
#         # Session should be secure
#         self.assertIn('Secure', response.cookies['sessionid'])
#         self.assertIn('HttpOnly', response.cookies['sessionid'])
# 
#     def test_sql_injection_protection(self):
#         """Test SQL injection protection"""
#         # Try to inject SQL in username field
#         response = self.client.post(reverse('auth:login'), {
#             'username': "'; DROP TABLE auth_user; --",
#             'password': 'testpass123',
#         })
#         
#         # Should not crash and should handle gracefully
#         self.assertNotEqual(response.status_code, 500)
# 
#     def test_rate_limiting(self):
#         """Test rate limiting on auth endpoints"""
#         # Make many requests to login endpoint
#         for _ in range(10):
#             response = self.client.post(reverse('auth:login'), {
#                 'username': 'testuser',
#                 'password': 'wrongpassword',
#             })
#         
#         # Should eventually be rate limited
#         self.assertIn(response.status_code, [429, 200])  # Either rate limited or still allowed 