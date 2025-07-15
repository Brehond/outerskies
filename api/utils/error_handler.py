"""
Comprehensive Error Handling System

This module provides consistent error handling across the application
with proper logging, user-friendly messages, and security considerations.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Union
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.conf import settings

logger = logging.getLogger('error_handler')


class ErrorHandler:
    """
    Centralized error handler for consistent error responses.
    """
    
    # Error type mappings
    ERROR_TYPES = {
        'validation': 'VALIDATION_ERROR',
        'permission': 'PERMISSION_DENIED',
        'not_found': 'NOT_FOUND',
        'rate_limit': 'RATE_LIMIT_EXCEEDED',
        'authentication': 'AUTHENTICATION_FAILED',
        'authorization': 'AUTHORIZATION_FAILED',
        'server_error': 'INTERNAL_SERVER_ERROR',
        'service_unavailable': 'SERVICE_UNAVAILABLE',
        'bad_request': 'BAD_REQUEST',
        'conflict': 'CONFLICT',
        'timeout': 'TIMEOUT',
    }
    
    # HTTP status code mappings
    STATUS_CODES = {
        'validation': 400,
        'permission': 403,
        'not_found': 404,
        'rate_limit': 429,
        'authentication': 401,
        'authorization': 403,
        'server_error': 500,
        'service_unavailable': 503,
        'bad_request': 400,
        'conflict': 409,
        'timeout': 408,
    }
    
    @classmethod
    def handle_exception(cls, request, exception) -> Optional[Response]:
        """
        Handle exceptions and return appropriate responses.
        """
        # Don't log DRF exceptions
        from rest_framework.exceptions import APIException
        if not isinstance(exception, APIException):
            cls._log_exception(request, exception)
        
        # Determine error type and status code
        error_type, status_code = cls._classify_exception(exception)
        
        # Create error response
        error_response = cls._create_error_response(
            error_type=error_type,
            message=cls._get_user_message(exception, error_type),
            details=cls._get_error_details(exception, error_type),
            status_code=status_code
        )
        
        return Response(error_response, status=status_code)
    
    @classmethod
    def handle_validation_error(cls, request, validation_error: ValidationError) -> Response:
        """
        Handle Django validation errors.
        """
        error_response = cls._create_error_response(
            error_type='validation',
            message='Validation failed',
            details=cls._format_validation_errors(validation_error),
            status_code=400
        )
        
        logger.warning(f'Validation error: {validation_error}')
        return Response(error_response, status=400)
    
    @classmethod
    def handle_permission_error(cls, request, permission_error: PermissionDenied) -> Response:
        """
        Handle permission denied errors.
        """
        error_response = cls._create_error_response(
            error_type='permission',
            message='Access denied',
            details={'reason': 'Insufficient permissions'},
            status_code=403
        )
        
        logger.warning(f'Permission denied: {permission_error}')
        return Response(error_response, status=403)
    
    @classmethod
    def handle_not_found_error(cls, request, not_found_error: Http404) -> Response:
        """
        Handle not found errors.
        """
        error_response = cls._create_error_response(
            error_type='not_found',
            message='Resource not found',
            details={'path': request.path},
            status_code=404
        )
        
        logger.info(f'Not found: {request.path}')
        return Response(error_response, status=404)
    
    @classmethod
    def handle_rate_limit_error(cls, request, limit_type: str, limit_info: Dict) -> Response:
        """
        Handle rate limit exceeded errors.
        """
        error_response = cls._create_error_response(
            error_type='rate_limit',
            message='Rate limit exceeded',
            details={
                'limit_type': limit_type,
                'retry_after': limit_info.get('retry_after', 3600),
                'current_limit': limit_info.get('current_limit', 0),
                'max_limit': limit_info.get('max_limit', 0)
            },
            status_code=429
        )
        
        logger.warning(f'Rate limit exceeded: {limit_type} by {cls._get_client_ip(request)}')
        return Response(error_response, status=429)
    
    @classmethod
    def handle_server_error(cls, request, exception: Exception) -> Response:
        """
        Handle internal server errors.
        """
        error_response = cls._create_error_response(
            error_type='server_error',
            message='Internal server error',
            details=cls._get_server_error_details(exception),
            status_code=500
        )
        
        logger.error(f'Server error: {exception}', exc_info=True)
        return Response(error_response, status=500)
    
    @classmethod
    def _classify_exception(cls, exception) -> tuple:
        """
        Classify exception and return error type and status code.
        """
        # Import DRF exceptions here to avoid circular imports
        from rest_framework.exceptions import NotAuthenticated, PermissionDenied as DRFPermissionDenied, ValidationError as DRFValidationError
        
        if isinstance(exception, (ValidationError, DRFValidationError)):
            return 'validation', 400
        elif isinstance(exception, (PermissionDenied, DRFPermissionDenied)):
            return 'permission', 403
        elif isinstance(exception, NotAuthenticated):
            return 'authentication', 401
        elif isinstance(exception, Http404):
            return 'not_found', 404
        elif isinstance(exception, TimeoutError):
            return 'timeout', 408
        elif isinstance(exception, ConnectionError):
            return 'service_unavailable', 503
        else:
            return 'server_error', 500
    
    @classmethod
    def _create_error_response(cls, error_type: str, message: str, 
                              details: Dict[str, Any], status_code: int) -> Dict[str, Any]:
        """
        Create a standardized error response.
        """
        response = {
            'error': {
                'type': cls.ERROR_TYPES.get(error_type, 'UNKNOWN_ERROR'),
                'message': message,
                'status_code': status_code,
                'timestamp': cls._get_timestamp(),
            }
        }
        
        # Add details if provided
        if details:
            response['error']['details'] = details
        
        # Add request ID if available
        if hasattr(settings, 'REQUEST_ID_HEADER'):
            response['error']['request_id'] = getattr(settings, 'REQUEST_ID', None)
        
        return response
    
    @classmethod
    def _get_user_message(cls, exception: Exception, error_type: str) -> str:
        """
        Get user-friendly error message.
        """
        if error_type == 'validation':
            return 'The provided data is invalid. Please check your input and try again.'
        elif error_type == 'permission':
            return 'You do not have permission to perform this action.'
        elif error_type == 'not_found':
            return 'The requested resource was not found.'
        elif error_type == 'rate_limit':
            return 'Too many requests. Please try again later.'
        elif error_type == 'authentication':
            return 'Authentication failed. Please log in again.'
        elif error_type == 'authorization':
            return 'You are not authorized to access this resource.'
        elif error_type == 'timeout':
            return 'The request timed out. Please try again.'
        elif error_type == 'service_unavailable':
            return 'Service temporarily unavailable. Please try again later.'
        else:
            return 'An unexpected error occurred. Please try again later.'
    
    @classmethod
    def _get_error_details(cls, exception: Exception, error_type: str) -> Dict[str, Any]:
        """
        Get error details for debugging (only in development).
        """
        if not settings.DEBUG:
            return {}
        
        details = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
        }
        
        if error_type == 'validation' and hasattr(exception, 'message_dict'):
            details['field_errors'] = exception.message_dict
        
        return details
    
    @classmethod
    def _get_server_error_details(cls, exception: Exception) -> Dict[str, Any]:
        """
        Get server error details (only in development).
        """
        if not settings.DEBUG:
            return {'message': 'Internal server error'}
        
        return {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc()
        }
    
    @classmethod
    def _format_validation_errors(cls, validation_error: ValidationError) -> Dict[str, Any]:
        """
        Format validation errors for response.
        """
        if hasattr(validation_error, 'message_dict'):
            return {'field_errors': validation_error.message_dict}
        elif hasattr(validation_error, 'messages'):
            return {'errors': list(validation_error.messages)}
        else:
            return {'error': str(validation_error)}
    
    @classmethod
    def _log_exception(cls, request, exception: Exception):
        """
        Log exception with context information.
        """
        # Don't log DRF exceptions as unexpected errors
        from rest_framework.exceptions import APIException
        if isinstance(exception, APIException):
            return
        
        log_data = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'request_path': getattr(request, 'path', 'unknown'),
            'request_method': getattr(request, 'method', 'unknown'),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'client_ip': cls._get_client_ip(request),
        }
        
        if isinstance(exception, (ValidationError, PermissionDenied, Http404)):
            logger.warning(f'Application error: {log_data}')
        else:
            logger.error(f'Unexpected error: {log_data}', exc_info=True)
    
    @classmethod
    def _get_client_ip(cls, request) -> str:
        """
        Get client IP address.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    @classmethod
    def _get_timestamp(cls) -> str:
        """
        Get current timestamp in ISO format.
        """
        from django.utils import timezone
        return timezone.now().isoformat()


# DRF exception handler
def drf_exception_handler(exc, context):
    """
    Custom exception handler for DRF.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        # Use our error handler for consistent formatting
        request = context['request']
        error_response = ErrorHandler.handle_exception(request, exc)
        return error_response
    
    return None


# Django middleware for handling exceptions
class ErrorHandlingMiddleware:
    """
    Middleware for handling Django exceptions.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Handle exceptions that occur during request processing.
        """
        # Don't handle exceptions for API views (handled by DRF)
        if request.path.startswith('/api/'):
            return None
        
        # Handle specific exception types
        if isinstance(exception, ValidationError):
            return ErrorHandler.handle_validation_error(request, exception)
        elif isinstance(exception, PermissionDenied):
            return ErrorHandler.handle_permission_error(request, exception)
        elif isinstance(exception, Http404):
            return ErrorHandler.handle_not_found_error(request, exception)
        else:
            return ErrorHandler.handle_server_error(request, exception)


# Utility functions for common error scenarios
def handle_api_error(error_type: str, message: str, details: Dict[str, Any] = None, 
                    status_code: int = None) -> Response:
    """
    Utility function for handling API errors.
    """
    if status_code is None:
        status_code = ErrorHandler.STATUS_CODES.get(error_type, 500)
    
    error_response = ErrorHandler._create_error_response(
        error_type=error_type,
        message=message,
        details=details or {},
        status_code=status_code
    )
    
    return Response(error_response, status=status_code)


def handle_validation_error(field_errors: Dict[str, Any], message: str = None) -> Response:
    """
    Utility function for handling validation errors.
    """
    return handle_api_error(
        error_type='validation',
        message=message or 'Validation failed',
        details={'field_errors': field_errors}
    )


def handle_permission_error(message: str = None) -> Response:
    """
    Utility function for handling permission errors.
    """
    return handle_api_error(
        error_type='permission',
        message=message or 'Access denied'
    )


def handle_not_found_error(resource: str = None) -> Response:
    """
    Utility function for handling not found errors.
    """
    message = f'{resource} not found' if resource else 'Resource not found'
    return handle_api_error(
        error_type='not_found',
        message=message
    ) 