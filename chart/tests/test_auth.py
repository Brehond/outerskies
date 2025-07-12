# from chart.middleware.auth import APIAuthMiddleware
from django.test import TestCase, RequestFactory, Client, override_settings
from django.http import HttpResponse
from datetime import datetime, timedelta
import json
from django.urls import reverse
from django.contrib.auth import get_user_model
from chart.models import Chart, PasswordResetToken
from django.utils import timezone
from django.core import mail
import uuid

User = get_user_model()

# class APIAuthMiddlewareTests(TestCase):
#     def setUp(self):
#         self.factory = RequestFactory()
#         self.middleware = APIAuthMiddleware()
#
#     def test_no_auth_for_static_files(self):
#         pass
#     def test_no_auth_for_non_api_endpoints(self):
#         pass
#     def test_no_auth_provided(self):
#         pass
#     def test_valid_jwt_token(self):
#         pass
#     def test_expired_jwt_token(self):
#         pass
#     def test_valid_api_key(self):
#         pass
#     def test_invalid_api_key(self):
#         pass
#     def test_api_key_path_restriction(self):
#         pass
#     def test_api_key_expiration(self):
#         pass


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@outer-skies.com',
    MIDDLEWARE=[
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
        "django_prometheus.middleware.PrometheusBeforeMiddleware",
        "django_prometheus.middleware.PrometheusAfterMiddleware",
        # Disable custom security middleware for tests
        # "chart.middleware.security.EnhancedSecurityMiddleware",
        # "chart.middleware.rate_limit.RateLimitMiddleware",
        # "chart.middleware.auth.APIAuthMiddleware",
        # "chart.middleware.validation.DataValidationMiddleware",
        # "chart.middleware.password.PasswordSecurityMiddleware",
        # "chart.middleware.file_upload.FileUploadSecurityMiddleware",
        # "chart.middleware.error_handling.ErrorHandlingMiddleware",
        # "chart.middleware.session.SessionSecurityMiddleware",
        # "chart.middleware.api_version.APIVersionMiddleware",
        # "chart.middleware.request_signing.RequestSigningMiddleware",
        # "chart.middleware.encryption.EncryptionMiddleware",
    ]
)
class TestAuthFlow(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('auth:register')
        self.login_url = reverse('auth:login')
        self.logout_url = reverse('auth:logout')
        self.profile_url = reverse('auth:profile')
        self.change_password_url = reverse('auth:change_password')
        self.password_reset_url = reverse('auth:password_reset_request')

    def test_registration_success(self):
        data = {
            'username': 'astrotest',
            'email': 'astro@example.com',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!',
            'agree_to_terms': True,
            'timezone': 'UTC',
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)  # Redirect after registration
        self.assertTrue(User.objects.filter(username='astrotest').exists())

    def test_registration_duplicate_username(self):
        User.objects.create_user(username='astrotest', email='astro1@example.com', password='Testpass123!')
        data = {
            'username': 'astrotest',
            'email': 'astro2@example.com',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!',
            'agree_to_terms': True,
            'timezone': 'UTC',
        }
        response = self.client.post(self.register_url, data)
        self.assertContains(response, 'This username is already taken', status_code=200)

    def test_registration_duplicate_email(self):
        User.objects.create_user(username='astrotest1', email='astro@example.com', password='Testpass123!')
        data = {
            'username': 'astrotest2',
            'email': 'astro@example.com',
            'password1': 'Testpass123!',
            'password2': 'Testpass123!',
            'agree_to_terms': True,
            'timezone': 'UTC',
        }
        response = self.client.post(self.register_url, data)
        self.assertContains(response, 'This email address is already registered', status_code=200)

    def test_registration_password_mismatch(self):
        data = {
            'username': 'astrotest',
            'email': 'astro@example.com',
            'password1': 'Testpass123!',
            'password2': 'Wrongpass!',
            'agree_to_terms': True,
            'timezone': 'UTC',
        }
        response = self.client.post(self.register_url, data)
        self.assertContains(response, "password fields didn", status_code=200)

    def test_login_logout_flow(self):
        _user = User.objects.create_user(username='astrotest', email='astro@example.com', password='Testpass123!')
        response = self.client.post(self.login_url, {'username': 'astrotest', 'password': 'Testpass123!'})
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_profile_update(self):
        user = User.objects.create_user(username='astrotest', email='astro@example.com', password='Testpass123!')
        self.client.login(username='astrotest', password='Testpass123!')
        response = self.client.post(self.profile_url, {
            'first_name': 'Astro',
            'last_name': 'Test',
            'email': 'astro@example.com',
            'birth_date': '2000-01-01',
            'birth_time': '12:00',
            'birth_location': 'New York',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'timezone': 'America/New_York',
            'preferred_zodiac_type': 'tropical',
            'preferred_house_system': 'placidus',
            'preferred_ai_model': 'gpt-4',
            'profile_public': True,
            'chart_history_public': False,
        })
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Astro')
        self.assertEqual(user.birth_location, 'New York')

    def test_password_change(self):
        user = User.objects.create_user(username='astrotest', email='astro@example.com', password='Testpass123!')
        self.client.login(username='astrotest', password='Testpass123!')
        response = self.client.post(self.change_password_url, {
            'old_password': 'Testpass123!',
            'new_password1': 'Newpass123!',
            'new_password2': 'Newpass123!',
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Newpass123!'))

    def test_password_reset_request_and_confirm(self):
        user = User.objects.create_user(username='astrotest', email='astro@example.com', password='Testpass123!')
        response = self.client.post(self.password_reset_url, {'email': 'astro@example.com'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        # Simulate clicking the reset link
        token = PasswordResetToken.objects.filter(user=user).first()
        self.assertIsNotNone(token)
        reset_url = reverse('auth:password_reset_confirm', args=[str(token.token)])
        response = self.client.post(reset_url, {
            'password1': 'Resetpass123!',
            'password2': 'Resetpass123!',
        })
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Resetpass123!'))

    def test_chart_model_and_history(self):
        user = User.objects.create_user(username='astrotest', email='astro@example.com', password='Testpass123!')
        chart = Chart.objects.create(
            user=user,
            name='Test Chart',
            birth_date='2000-01-01',
            birth_time='12:00',
            latitude=40.7128,
            longitude=-74.0060,
            location_name='New York',
            timezone='America/New_York',
            zodiac_type='tropical',
            house_system='placidus',
            ai_model_used='gpt-4',
            chart_data={},
            planetary_positions={},
            house_positions={},
            aspects={},
        )
        self.assertEqual(chart.user, user)
        self.assertEqual(chart.name, 'Test Chart')
        self.client.login(username='astrotest', password='Testpass123!')
        response = self.client.get(reverse('auth:chart_history'))
        self.assertContains(response, 'Test Chart')

    def test_chart_delete_and_favorite(self):
        user = User.objects.create_user(username='astrotest', email='astro@example.com', password='Testpass123!')
        chart = Chart.objects.create(
            user=user,
            name='Test Chart',
            birth_date='2000-01-01',
            birth_time='12:00',
            latitude=40.7128,
            longitude=-74.0060,
            location_name='New York',
            timezone='America/New_York',
            zodiac_type='tropical',
            house_system='placidus',
            ai_model_used='gpt-4',
            chart_data={},
            planetary_positions={},
            house_positions={},
            aspects={},
        )
        self.client.login(username='astrotest', password='Testpass123!')
        delete_url = reverse('auth:delete_chart', args=[str(chart.id)])
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Chart.objects.filter(id=chart.id).exists())
        # Re-create and test favorite toggle
        chart = Chart.objects.create(
            user=user,
            name='Test Chart',
            birth_date='2000-01-01',
            birth_time='12:00',
            latitude=40.7128,
            longitude=-74.0060,
            location_name='New York',
            timezone='America/New_York',
            zodiac_type='tropical',
            house_system='placidus',
            ai_model_used='gpt-4',
            chart_data={},
            planetary_positions={},
            house_positions={},
            aspects={},
        )
        toggle_url = reverse('auth:toggle_favorite_chart', args=[str(chart.id)])
        response = self.client.post(toggle_url)
        chart.refresh_from_db()
        self.assertTrue(chart.is_favorite)

    def test_url_permissions(self):
        # Unauthenticated users should be redirected from profile and chart history
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('auth:chart_history'))
        self.assertEqual(response.status_code, 302)
        # Registration and login should be accessible
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_registration(self):
        response = self.client.post(reverse('auth:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'agree_to_terms': True,
            'timezone': 'UTC',
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(User.objects.filter(username='newuser').exists())
