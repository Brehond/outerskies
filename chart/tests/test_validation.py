import os
import django
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from chart.middleware.validation import DataValidationMiddleware
import json
from datetime import datetime

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chart.tests.test_settings')
django.setup()

class DataValidationMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = DataValidationMiddleware(get_response=lambda r: HttpResponse())
        
        # Sample valid data
        self.valid_chart_data = {
            'title': 'Test Chart',
            'description': 'A test chart',
            'data': [
                {'x': 1, 'y': 10},
                {'x': 2, 'y': 20},
                {'x': 3, 'y': 30}
            ],
            'options': {
                'type': 'line',
                'colors': ['#ff0000', '#00ff00'],
                'showLegend': True
            }
        }
        
        self.valid_data_points = {
            'data': [
                {
                    'value': 42.5,
                    'timestamp': '2024-03-20T12:00:00.000Z'
                }
            ]
        }

    def test_skip_validation_for_non_api_endpoints(self):
        """Test that validation is skipped for non-API endpoints."""
        request = self.factory.post('/some/path/', data={'key': 'value'})
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_skip_validation_for_get_requests(self):
        """Test that validation is skipped for GET requests."""
        request = self.factory.get('/api/chart/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_valid_chart_data(self):
        """Test that valid chart data passes validation."""
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(self.valid_chart_data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.validated_data['title'], 'Test Chart')

    def test_missing_required_field(self):
        """Test that missing required fields are caught."""
        data = self.valid_chart_data.copy()
        del data['title']
        
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('Missing required field: title', data['details'])

    def test_invalid_field_type(self):
        """Test that invalid field types are caught."""
        data = self.valid_chart_data.copy()
        data['title'] = 123  # Should be string
        
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Field 'title' must be of type string", data['details'])

    def test_string_length_validation(self):
        """Test that string length validation works."""
        data = self.valid_chart_data.copy()
        data['title'] = 'a' * 101  # Exceeds maxLength of 100
        
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Field 'title' must be at most 100 characters", data['details'])

    def test_enum_validation(self):
        """Test that enum validation works."""
        data = self.valid_chart_data.copy()
        data['options']['type'] = 'invalid'  # Not in enum
        
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Field 'options.type' must be one of: ['line', 'bar', 'pie']", data['details'])

    def test_array_validation(self):
        """Test that array validation works."""
        data = self.valid_chart_data.copy()
        data['data'] = [{'x': 'invalid', 'y': 'invalid'}]  # Invalid types
        
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Field 'data[0].y' must be a valid number", data['details'])

    def test_html_sanitization(self):
        """Test that HTML is stripped from strings."""
        data = self.valid_chart_data.copy()
        data['title'] = '<script>alert("xss")</script>Test Chart'
        
        request = self.factory.post(
            '/api/chart/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.validated_data['title'], '<script>alert("xss")</script>Test Chart')

    def test_number_sanitization(self):
        """Test that numbers are properly sanitized."""
        data = self.valid_data_points.copy()
        data['data'][0]['value'] = '42.5'  # String number
        
        request = self.factory.post(
            '/api/data/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.validated_data['data'][0]['value'], 42.5)

    def test_date_validation(self):
        """Test that date validation works."""
        data = self.valid_data_points.copy()
        data['data'][0]['timestamp'] = 'invalid-date'
        
        request = self.factory.post(
            '/api/data/',
            data=json.dumps(data),
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("Field 'data[0].timestamp' must be a valid date in format", data['details'][0])

    def test_invalid_json(self):
        """Test that invalid JSON is caught."""
        request = self.factory.post(
            '/api/chart/',
            data='invalid json',
            content_type='application/json'
        )
        response = self.middleware(request)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Invalid JSON data') 