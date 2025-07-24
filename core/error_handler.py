"""
Centralized Error Handler for Outer Skies

This module provides a single, consistent error handling system
that replaces the fragmented error handling across the application.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from django.conf import settings
from django.utils import timezone

from .exceptions import (
    OuterSkiesException, ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, RateLimitExceededError, ExternalServiceError,
    SecurityError, convert_django_exception
)

logger = logging.getLogger('error_handler')


class ErrorHandler:
    """
    Centralized error handler for consistent error responses.
    """
    
    @classmethod
    def handle_exception(cls, request, exception) -> Optional[Response]:
        """
        Handle exceptions and return appropriate responses.
        """
        # Convert Django exceptions to OuterSkies exceptions
        if not isinstance(exception, OuterSkiesException):
            exception = convert_django_exception(exception)
        
        # Log the exception
        cls._log_exception(request, exception)
        
        # Create error response
        error_response = cls._create_error_response(exception)
        
        return Response(error_response, status=exception.status_code)
    
    @classmethod
    def handle_validation_error(cls, request, validation_error: DjangoValidationError) -> Response:
        """Handle Django validation errors."""
        # Convert to our ValidationError
        if hasattr(validation_error, 'message_dict'):
            field_errors = validation_error.message_dict
        else:
            field_errors = {'non_field_errors': [str(validation_error)]}
        
        exception = ValidationError("Validation failed", field_errors)
        return cls.handle_exception(request, exception)
    
    @classmethod
    def handle_permission_error(cls, request, permission_error: PermissionDenied) -> Response:
        """Handle permission denied errors."""
        exception = AuthorizationError("Access denied")
        return cls.handle_exception(request, exception)
    
    @classmethod
    def handle_not_found_error(cls, request, not_found_error: Http404) -> Response:
        """Handle not found errors."""
        exception = ResourceNotFoundError("Resource", request.path)
        return cls.handle_exception(request, exception)
    
    @classmethod
    def handle_rate_limit_error(cls, request, limit_type: str, limit_info: Dict) -> Response:
        """Handle rate limit exceeded errors."""
        exception = RateLimitExceededError(
            limit_type=limit_type,
            limit=limit_info.get('limit', 0),
            window=limit_info.get('window', 3600),
            retry_after=limit_info.get('retry_after', 3600)
        )
        return cls.handle_exception(request, exception)
    
    @classmethod
    def handle_security_error(cls, request, security_error: SecurityError) -> Response:
        """Handle security errors."""
        return cls.handle_exception(request, security_error)
    
    @classmethod
    def _create_error_response(cls, exception: OuterSkiesException) -> Dict[str, Any]:
        """Create a standardized error response."""
        response = {
            'error': {
                'code': exception.error_code,
                'message': exception.user_message,
                'status_code': exception.status_code,
                'timestamp': timezone.now().isoformat(),
                'request_id': cls._get_request_id(),
            }
        }
        
        # Add details if provided
        if exception.details:
            response['error']['details'] = exception.details
        
        # Add debug information in development
        if settings.DEBUG:
            response['error']['debug'] = {
                'exception_type': type(exception).__name__,
                'internal_message': exception.message,
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }
        
        return response
    
    @classmethod
    def _log_exception(cls, request, exception: OuterSkiesException):
        """Log exception with appropriate level."""
        client_ip = cls._get_client_ip(request)
        user_id = request.user.id if request.user.is_authenticated else None
        
        log_data = {
            'exception_type': type(exception).__name__,
            'error_code': exception.error_code,
            'status_code': exception.status_code,
            'client_ip': client_ip,
            'user_id': user_id,
            'request_path': request.path,
            'request_method': request.method,
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'details': exception.details
        }
        
        # Log based on severity
        if exception.status_code >= 500:
            logger.error(f"Server error: {exception.message}", extra=log_data, exc_info=True)
        elif exception.status_code >= 400:
            logger.warning(f"Client error: {exception.message}", extra=log_data)
        else:
            logger.info(f"Application error: {exception.message}", extra=log_data)
    
    @classmethod
    def _get_client_ip(cls, request) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    @classmethod
    def _get_request_id(cls) -> Optional[str]:
        """Get request ID if available."""
        # This could be set by middleware
        return getattr(settings, 'REQUEST_ID', None)


# DRF Exception Handler
def drf_exception_handler(exc, context):
    """
    Custom DRF exception handler that uses our centralized error handling.
    """
    # Let DRF handle its own exceptions first
    response = drf_exception_handler(exc, context)
    
    if response is None:
        # Handle with our error handler
        request = context['request']
        return ErrorHandler.handle_exception(request, exc)
    
    return response


# Django Middleware for Error Handling
class ErrorHandlingMiddleware:
    """
    Django middleware for centralized error handling.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.get_response(request)
    
    def process_exception(self, request, exception):
        """Process exceptions in Django views."""
        # Don't handle DRF exceptions here (they're handled by DRF)
        if hasattr(request, 'accepted_renderer'):
            return None
        
        # Handle with our error handler
        return ErrorHandler.handle_exception(request, exception)


# Utility functions for common error responses
def handle_api_error(exception: OuterSkiesException, context: str = None) -> Response:
    """Handle API errors with context."""
    if context:
        logger.warning(f"Error in {context}: {exception.message}")
    return ErrorHandler.handle_exception(None, exception)


def handle_validation_error(field_errors: Dict[str, Any], message: str = None) -> Response:
    """Handle validation errors."""
    exception = ValidationError(message or "Validation failed", field_errors)
    return ErrorHandler.handle_exception(None, exception)


def handle_permission_error(message: str = None) -> Response:
    """Handle permission errors."""
    exception = AuthorizationError(message or "Access denied")
    return ErrorHandler.handle_exception(None, exception)


def handle_not_found_error(resource_type: str = "Resource", resource_id: str = "unknown") -> Response:
    """Handle not found errors."""
    exception = ResourceNotFoundError(resource_type, resource_id)
    return ErrorHandler.handle_exception(None, exception)


def handle_external_service_error(service_name: str, message: str = None, details: Dict[str, Any] = None) -> Response:
    """Handle external service errors."""
    exception = ExternalServiceError(service_name, message or "Service unavailable", details)
    return ErrorHandler.handle_exception(None, exception)


# Decorator for automatic error handling
def handle_errors(func):
    """Decorator to automatically handle errors in views."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Get request from args (assuming it's the first argument)
            request = args[0] if args else None
            return ErrorHandler.handle_exception(request, e)
    return wrapper


# Context manager for error handling
class ErrorContext:
    """Context manager for error handling."""
    
    def __init__(self, context_name: str, default_response: Response = None):
        self.context_name = context_name
        self.default_response = default_response
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            logger.error(f"Error in {self.context_name}: {exc_val}")
            if self.default_response:
                return self.default_response
        return False 