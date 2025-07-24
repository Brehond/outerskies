"""
Standardized API Response System

This module provides consistent API response formatting across all endpoints,
ensuring uniform error handling, success responses, and data structure.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

from .exceptions import OuterSkiesException

logger = logging.getLogger(__name__)


class APIResponse:
    """Standardized API response formatter."""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success", 
                status_code: int = status.HTTP_200_OK,
                meta: Optional[Dict[str, Any]] = None) -> Response:
        """
        Create a standardized success response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code
            meta: Additional metadata
            
        Returns:
            Formatted Response object
        """
        response_data = {
            'status': 'success',
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        if meta:
            response_data['meta'] = meta
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(message: str, error_code: str = "GENERAL_ERROR",
              status_code: int = status.HTTP_400_BAD_REQUEST,
              details: Optional[Dict[str, Any]] = None,
              data: Any = None) -> Response:
        """
        Create a standardized error response.
        
        Args:
            message: Error message
            error_code: Application-specific error code
            status_code: HTTP status code
            details: Additional error details
            data: Additional data (e.g., validation errors)
            
        Returns:
            Formatted Response object
        """
        response_data = {
            'status': 'error',
            'error': {
                'code': error_code,
                'message': message
            },
            'timestamp': datetime.now().isoformat()
        }
        
        if details:
            response_data['error']['details'] = details
            
        if data:
            response_data['data'] = data
            
        return Response(response_data, status=status_code)
    
    @staticmethod
    def validation_error(errors: Dict[str, Any], 
                        message: str = "Validation failed") -> Response:
        """
        Create a standardized validation error response.
        
        Args:
            errors: Validation error details
            message: Error message
            
        Returns:
            Formatted Response object
        """
        return APIResponse.error(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            data=errors
        )
    
    @staticmethod
    def not_found(resource: str, identifier: str,
                  message: Optional[str] = None) -> Response:
        """
        Create a standardized not found response.
        
        Args:
            resource: Type of resource (e.g., "User", "Chart")
            identifier: Resource identifier
            message: Custom error message
            
        Returns:
            Formatted Response object
        """
        if not message:
            message = f"{resource} with identifier '{identifier}' not found"
            
        return APIResponse.error(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details={'resource': resource, 'identifier': identifier}
        )
    
    @staticmethod
    def forbidden(message: str = "Access denied",
                  details: Optional[Dict[str, Any]] = None) -> Response:
        """
        Create a standardized forbidden response.
        
        Args:
            message: Error message
            details: Additional details
            
        Returns:
            Formatted Response object
        """
        return APIResponse.error(
            message=message,
            error_code="FORBIDDEN",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )
    
    @staticmethod
    def unauthorized(message: str = "Authentication required",
                    details: Optional[Dict[str, Any]] = None) -> Response:
        """
        Create a standardized unauthorized response.
        
        Args:
            message: Error message
            details: Additional details
            
        Returns:
            Formatted Response object
        """
        return APIResponse.error(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )
    
    @staticmethod
    def server_error(message: str = "Internal server error",
                    details: Optional[Dict[str, Any]] = None) -> Response:
        """
        Create a standardized server error response.
        
        Args:
            message: Error message
            details: Additional details
            
        Returns:
            Formatted Response object
        """
        return APIResponse.error(
            message=message,
            error_code="INTERNAL_SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )
    
    @staticmethod
    def paginated(data: List[Any], total: int, page: int, 
                  page_size: int, message: str = "Data retrieved successfully",
                  meta: Optional[Dict[str, Any]] = None) -> Response:
        """
        Create a standardized paginated response.
        
        Args:
            data: List of items
            total: Total number of items
            page: Current page number
            page_size: Items per page
            message: Success message
            meta: Additional metadata
            
        Returns:
            Formatted Response object
        """
        pagination_meta = {
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': (total + page_size - 1) // page_size,
                'has_next': page * page_size < total,
                'has_previous': page > 1
            }
        }
        
        if meta:
            pagination_meta.update(meta)
            
        return APIResponse.success(
            data=data,
            message=message,
            meta=pagination_meta
        )


def handle_api_exception(func):
    """
    Decorator to handle API exceptions and return standardized responses.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except OuterSkiesException as e:
            logger.warning(f"API exception in {func.__name__}: {e}")
            return APIResponse.error(
                message=str(e),
                error_code=e.error_code,
                status_code=e.status_code,
                details=e.details
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return APIResponse.server_error(
                message="An unexpected error occurred",
                details={'function': func.__name__} if settings.DEBUG else None
            )
    return wrapper


# Convenience functions for common responses
def success_response(data: Any = None, message: str = "Success", 
                    status_code: int = status.HTTP_200_OK,
                    meta: Optional[Dict[str, Any]] = None) -> Response:
    """Convenience function for success responses."""
    return APIResponse.success(data, message, status_code, meta)


def error_response(message: str, error_code: str = "GENERAL_ERROR",
                  status_code: int = status.HTTP_400_BAD_REQUEST,
                  details: Optional[Dict[str, Any]] = None,
                  data: Any = None) -> Response:
    """Convenience function for error responses."""
    return APIResponse.error(message, error_code, status_code, details, data)


def validation_response(errors: Dict[str, Any], 
                       message: str = "Validation failed") -> Response:
    """Convenience function for validation error responses."""
    return APIResponse.validation_error(errors, message)


def not_found_response(resource: str, identifier: str,
                      message: Optional[str] = None) -> Response:
    """Convenience function for not found responses."""
    return APIResponse.not_found(resource, identifier, message)


def paginated_response(data: List[Any], total: int, page: int, 
                      page_size: int, message: str = "Data retrieved successfully",
                      meta: Optional[Dict[str, Any]] = None) -> Response:
    """Convenience function for paginated responses."""
    return APIResponse.paginated(data, total, page, page_size, message, meta) 