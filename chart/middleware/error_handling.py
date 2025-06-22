import json
import logging
import traceback
from django.conf import settings
from django.http import JsonResponse, HttpResponseServerError
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.views.debug import get_exception_reporter_filter
from django.core.cache import cache
import hashlib
import time

logger = logging.getLogger('security')

class ErrorHandlingMiddleware:
    """
    Error handling middleware that provides:
    - Custom error pages
    - Error logging
    - Error reporting
    - Error tracking
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.error_email = getattr(settings, 'ERROR_EMAIL', 'admin@example.com')
        self.error_threshold = getattr(settings, 'ERROR_THRESHOLD', 5)  # errors per minute
        self.error_window = getattr(settings, 'ERROR_WINDOW', 60)  # seconds
        self.track_errors = getattr(settings, 'TRACK_ERRORS', True)
        self.report_errors = getattr(settings, 'REPORT_ERRORS', True)
        
    def __call__(self, request):
        try:
            response = self.get_response(request)
            
            # Handle 4xx and 5xx responses
            if 400 <= response.status_code < 600:
                self._handle_error_response(request, response)
                
            return response
            
        except Exception as e:
            return self._handle_exception(request, e)
            
    def _handle_error_response(self, request, response):
        """Handle error responses."""
        # Log the error
        self._log_error(request, response)
        
        # Track the error
        if self.track_errors:
            self._track_error(request, response)
            
        # Report the error
        if self.report_errors and response.status_code >= 500:
            self._report_error(request, response)
            
        # Customize error response
        if request.content_type == 'application/json':
            return self._json_error_response(response)
        else:
            return self._html_error_response(response)
            
    def _handle_exception(self, request, exception):
        """Handle uncaught exceptions."""
        # Log the exception
        self._log_exception(request, exception)
        
        # Track the exception
        if self.track_errors:
            self._track_exception(request, exception)
            
        # Report the exception
        if self.report_errors:
            self._report_exception(request, exception)
            
        # Return appropriate response
        if request.content_type == 'application/json':
            return self._json_exception_response(exception)
        else:
            return self._html_exception_response(exception)
            
    def _log_error(self, request, response):
        """Log error response."""
        error_data = {
            'status_code': response.status_code,
            'path': request.path,
            'method': request.method,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'timestamp': time.time()
        }
        
        logger.error(f"Error response: {json.dumps(error_data)}")
        
    def _log_exception(self, request, exception):
        """Log exception."""
        error_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'path': request.path,
            'method': request.method,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'timestamp': time.time(),
            'traceback': traceback.format_exc()
        }
        
        logger.error(f"Uncaught exception: {json.dumps(error_data)}")
        
    def _track_error(self, request, response):
        """Track error for rate limiting."""
        key = f'error_count_{self._get_client_ip(request)}'
        current_time = int(time.time())
        
        # Get current error count
        error_data = cache.get(key, {'count': 0, 'window_start': current_time})
        
        # Reset counter if window has expired
        if current_time - error_data['window_start'] >= self.error_window:
            error_data = {'count': 0, 'window_start': current_time}
            
        # Increment counter
        error_data['count'] += 1
        cache.set(key, error_data, self.error_window)
        
    def _track_exception(self, request, exception):
        """Track exception for rate limiting."""
        key = f'error_count_{self._get_client_ip(request)}'
        current_time = int(time.time())
        
        # Get current error count
        error_data = cache.get(key, {'count': 0, 'window_start': current_time})
        
        # Reset counter if window has expired
        if current_time - error_data['window_start'] >= self.error_window:
            error_data = {'count': 0, 'window_start': current_time}
            
        # Increment counter
        error_data['count'] += 1
        cache.set(key, error_data, self.error_window)
        
    def _report_error(self, request, response):
        """Report error to admin."""
        if not self._should_report_error(request):
            return
            
        error_data = {
            'status_code': response.status_code,
            'path': request.path,
            'method': request.method,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'timestamp': time.time()
        }
        
        # Send email
        subject = f'Error {response.status_code} on {request.path}'
        message = json.dumps(error_data, indent=2)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.error_email])
        
    def _report_exception(self, request, exception):
        """Report exception to admin."""
        if not self._should_report_error(request):
            return
            
        error_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'path': request.path,
            'method': request.method,
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT'),
            'timestamp': time.time(),
            'traceback': traceback.format_exc()
        }
        
        # Send email
        subject = f'Uncaught exception: {type(exception).__name__}'
        message = json.dumps(error_data, indent=2)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.error_email])
        
    def _should_report_error(self, request):
        """Check if error should be reported based on rate limiting."""
        key = f'error_count_{self._get_client_ip(request)}'
        error_data = cache.get(key, {'count': 0, 'window_start': time.time()})
        return error_data['count'] <= self.error_threshold
        
    def _json_error_response(self, response):
        """Return JSON error response."""
        return JsonResponse({
            'error': 'An error occurred',
            'status_code': response.status_code
        }, status=response.status_code)
        
    def _json_exception_response(self, exception):
        """Return JSON exception response."""
        return JsonResponse({
            'error': 'An unexpected error occurred',
            'type': type(exception).__name__
        }, status=500)
        
    def _html_error_response(self, response):
        """Return HTML error response."""
        context = {
            'status_code': response.status_code,
            'error_message': response.reason_phrase
        }
        return HttpResponseServerError(
            render_to_string('error.html', context)
        )
        
    def _html_exception_response(self, exception):
        """Return HTML exception response."""
        context = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception)
        }
        return HttpResponseServerError(
            render_to_string('error.html', context)
        )
        
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR') 