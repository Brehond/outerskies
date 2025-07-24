"""
API Standardization Service

This module provides API standardization features including:
- Consistent response formats
- Comprehensive error handling
- Standardized API documentation
- Request/response validation
- API versioning support
- Rate limiting integration
- Performance monitoring
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from django.http import JsonResponse, HttpResponse
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException
import traceback

logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """Standard response status codes."""
    SUCCESS = 'success'
    ERROR = 'error'
    WARNING = 'warning'
    INFO = 'info'


class ErrorCode(Enum):
    """Standard error codes."""
    # Authentication errors
    UNAUTHORIZED = 'AUTH_001'
    FORBIDDEN = 'AUTH_002'
    INVALID_TOKEN = 'AUTH_003'
    TOKEN_EXPIRED = 'AUTH_004'
    
    # Validation errors
    VALIDATION_ERROR = 'VAL_001'
    INVALID_INPUT = 'VAL_002'
    MISSING_REQUIRED_FIELD = 'VAL_003'
    INVALID_FORMAT = 'VAL_004'
    
    # Business logic errors
    RESOURCE_NOT_FOUND = 'BUS_001'
    RESOURCE_EXISTS = 'BUS_002'
    INSUFFICIENT_PERMISSIONS = 'BUS_003'
    QUOTA_EXCEEDED = 'BUS_004'
    RATE_LIMIT_EXCEEDED = 'BUS_005'
    
    # System errors
    INTERNAL_ERROR = 'SYS_001'
    SERVICE_UNAVAILABLE = 'SYS_002'
    DATABASE_ERROR = 'SYS_003'
    CACHE_ERROR = 'SYS_004'
    EXTERNAL_SERVICE_ERROR = 'SYS_005'
    
    # Background task errors
    TASK_NOT_FOUND = 'TASK_001'
    TASK_FAILED = 'TASK_002'
    TASK_TIMEOUT = 'TASK_003'
    TASK_CANCELLED = 'TASK_004'


@dataclass
class APIResponse:
    """Standardized API response structure."""
    status: ResponseStatus
    data: Optional[Any] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    request_id: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.version is None:
            self.version = 'v1'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        response = {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version
        }
        
        if self.data is not None:
            response['data'] = self.data
        
        if self.message is not None:
            response['message'] = self.message
        
        if self.error_code is not None:
            response['error_code'] = self.error_code
        
        if self.error_details is not None:
            response['error_details'] = self.error_details
        
        if self.request_id is not None:
            response['request_id'] = self.request_id
        
        if self.metadata is not None:
            response['metadata'] = self.metadata
        
        return response


@dataclass
class APIError:
    """Standardized API error structure."""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    http_status: int = 400
    
    def to_response(self, request_id: Optional[str] = None) -> APIResponse:
        """Convert error to API response."""
        return APIResponse(
            status=ResponseStatus.ERROR,
            message=self.message,
            error_code=self.code.value,
            error_details=self.details,
            request_id=request_id
        )


class APIStandardizer:
    """
    API standardization service that provides consistent response formats
    and comprehensive error handling.
    """
    
    def __init__(self):
        self.error_mappings = {
            ValidationError: ErrorCode.VALIDATION_ERROR,
            PermissionDenied: ErrorCode.FORBIDDEN,
            APIException: ErrorCode.INTERNAL_ERROR,
            KeyError: ErrorCode.VALIDATION_ERROR,
            ValueError: ErrorCode.VALIDATION_ERROR,
            TypeError: ErrorCode.VALIDATION_ERROR,
        }
        
        self.default_messages = {
            ErrorCode.UNAUTHORIZED: "Authentication required",
            ErrorCode.FORBIDDEN: "Access denied",
            ErrorCode.VALIDATION_ERROR: "Validation error occurred",
            ErrorCode.RESOURCE_NOT_FOUND: "Resource not found",
            ErrorCode.INTERNAL_ERROR: "Internal server error",
            ErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded",
            ErrorCode.QUOTA_EXCEEDED: "Usage quota exceeded",
        }
    
    def success_response(self, data: Any = None, message: str = None,
                        request_id: str = None, metadata: Dict[str, Any] = None) -> APIResponse:
        """
        Create a standardized success response.
        
        Args:
            data: Response data
            message: Success message
            request_id: Request ID for tracking
            metadata: Additional metadata
            
        Returns:
            Standardized API response
        """
        return APIResponse(
            status=ResponseStatus.SUCCESS,
            data=data,
            message=message,
            request_id=request_id,
            metadata=metadata
        )
    
    def error_response(self, error: Union[Exception, ErrorCode, str],
                      message: str = None, details: Dict[str, Any] = None,
                      request_id: str = None) -> APIResponse:
        """
        Create a standardized error response.
        
        Args:
            error: Error object, code, or message
            message: Error message
            details: Error details
            request_id: Request ID for tracking
            
        Returns:
            Standardized API response
        """
        if isinstance(error, ErrorCode):
            error_code = error
            if message is None:
                message = self.default_messages.get(error, str(error))
        elif isinstance(error, Exception):
            error_code = self._map_exception_to_error_code(error)
            if message is None:
                message = str(error)
        else:
            error_code = ErrorCode.INTERNAL_ERROR
            if message is None:
                message = str(error)
        
        return APIResponse(
            status=ResponseStatus.ERROR,
            message=message,
            error_code=error_code.value,
            error_details=details,
            request_id=request_id
        )
    
    def warning_response(self, message: str, data: Any = None,
                        request_id: str = None) -> APIResponse:
        """
        Create a standardized warning response.
        
        Args:
            message: Warning message
            data: Response data
            request_id: Request ID for tracking
            
        Returns:
            Standardized API response
        """
        return APIResponse(
            status=ResponseStatus.WARNING,
            data=data,
            message=message,
            request_id=request_id
        )
    
    def info_response(self, message: str, data: Any = None,
                     request_id: str = None) -> APIResponse:
        """
        Create a standardized info response.
        
        Args:
            message: Info message
            data: Response data
            request_id: Request ID for tracking
            
        Returns:
            Standardized API response
        """
        return APIResponse(
            status=ResponseStatus.INFO,
            data=data,
            message=message,
            request_id=request_id
        )
    
    def to_json_response(self, api_response: APIResponse, 
                        http_status: int = 200) -> JsonResponse:
        """
        Convert API response to Django JsonResponse.
        
        Args:
            api_response: Standardized API response
            http_status: HTTP status code
            
        Returns:
            Django JsonResponse
        """
        return JsonResponse(
            api_response.to_dict(),
            status=http_status,
            content_type='application/json'
        )
    
    def to_drf_response(self, api_response: APIResponse,
                       http_status: int = 200) -> Response:
        """
        Convert API response to DRF Response.
        
        Args:
            api_response: Standardized API response
            http_status: HTTP status code
            
        Returns:
            DRF Response
        """
        return Response(
            api_response.to_dict(),
            status=http_status
        )
    
    def handle_exception(self, exception: Exception, request_id: str = None) -> APIResponse:
        """
        Handle exceptions and convert to standardized error response.
        
        Args:
            exception: Exception to handle
            request_id: Request ID for tracking
            
        Returns:
            Standardized error response
        """
        # Log the exception
        logger.error(f"API Exception: {type(exception).__name__}: {str(exception)}")
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        
        # Map exception to error code
        error_code = self._map_exception_to_error_code(exception)
        
        # Get error details
        error_details = self._get_error_details(exception)
        
        # Create error response
        return self.error_response(
            error=error_code,
            message=str(exception),
            details=error_details,
            request_id=request_id
        )
    
    def validate_request_data(self, data: Dict[str, Any], 
                            required_fields: List[str] = None,
                            optional_fields: List[str] = None) -> Dict[str, Any]:
        """
        Validate request data against required and optional fields.
        
        Args:
            data: Request data to validate
            required_fields: List of required field names
            optional_fields: List of optional field names
            
        Returns:
            Validated data
            
        Raises:
            ValidationError: If validation fails
        """
        if required_fields is None:
            required_fields = []
        
        if optional_fields is None:
            optional_fields = []
        
        validated_data = {}
        missing_fields = []
        
        # Check required fields
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
            else:
                validated_data[field] = data[field]
        
        # Add optional fields if present
        for field in optional_fields:
            if field in data:
                validated_data[field] = data[field]
        
        # Raise error if required fields are missing
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        return validated_data
    
    def paginate_response(self, data: List[Any], page: int = 1, 
                         page_size: int = 20, total_count: int = None) -> Dict[str, Any]:
        """
        Create a paginated response structure.
        
        Args:
            data: List of items to paginate
            page: Current page number
            page_size: Number of items per page
            total_count: Total number of items
            
        Returns:
            Paginated response structure
        """
        if total_count is None:
            total_count = len(data)
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
            'items': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_previous': page > 1
            }
        }
    
    def add_metadata(self, response: APIResponse, 
                    metadata: Dict[str, Any]) -> APIResponse:
        """
        Add metadata to an API response.
        
        Args:
            response: API response to modify
            metadata: Metadata to add
            
        Returns:
            Modified API response
        """
        if response.metadata is None:
            response.metadata = {}
        
        response.metadata.update(metadata)
        return response
    
    def add_performance_metrics(self, response: APIResponse,
                               start_time: float) -> APIResponse:
        """
        Add performance metrics to an API response.
        
        Args:
            response: API response to modify
            start_time: Request start time
            
        Returns:
            Modified API response with performance metrics
        """
        processing_time = time.time() - start_time
        
        metadata = {
            'processing_time_ms': round(processing_time * 1000, 2),
            'timestamp': datetime.now().isoformat()
        }
        
        return self.add_metadata(response, metadata)
    
    def create_api_documentation(self, endpoint: str, method: str,
                               description: str, parameters: List[Dict[str, Any]] = None,
                               responses: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create standardized API documentation.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            description: Endpoint description
            parameters: List of parameters
            responses: List of possible responses
            
        Returns:
            API documentation structure
        """
        return {
            'endpoint': endpoint,
            'method': method.upper(),
            'description': description,
            'parameters': parameters or [],
            'responses': responses or [],
            'examples': self._generate_examples(endpoint, method),
            'rate_limits': self._get_rate_limits(endpoint),
            'authentication': self._get_auth_requirements(endpoint)
        }
    
    def _map_exception_to_error_code(self, exception: Exception) -> ErrorCode:
        """Map exception to error code."""
        exception_type = type(exception)
        
        # Check direct mapping
        if exception_type in self.error_mappings:
            return self.error_mappings[exception_type]
        
        # Check inheritance
        for exc_type, error_code in self.error_mappings.items():
            if isinstance(exception, exc_type):
                return error_code
        
        # Default to internal error
        return ErrorCode.INTERNAL_ERROR
    
    def _get_error_details(self, exception: Exception) -> Dict[str, Any]:
        """Get detailed error information."""
        details = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception)
        }
        
        # Add specific details for common exceptions
        if isinstance(exception, ValidationError):
            if hasattr(exception, 'message_dict'):
                details['validation_errors'] = exception.message_dict
            elif hasattr(exception, 'messages'):
                details['validation_errors'] = exception.messages
        
        elif isinstance(exception, PermissionDenied):
            details['permission_required'] = 'User does not have required permissions'
        
        return details
    
    def _generate_examples(self, endpoint: str, method: str) -> Dict[str, Any]:
        """Generate example requests and responses."""
        # This is a simplified implementation
        # In production, you'd have more sophisticated example generation
        return {
            'request': {
                'method': method.upper(),
                'url': f'/api/v1{endpoint}',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer <token>'
                },
                'body': {}
            },
            'response': {
                'status': 200,
                'body': {
                    'status': 'success',
                    'data': {},
                    'timestamp': '2025-01-01T00:00:00Z',
                    'version': 'v1'
                }
            }
        }
    
    def _get_rate_limits(self, endpoint: str) -> Dict[str, Any]:
        """Get rate limit information for endpoint."""
        # This is a simplified implementation
        # In production, you'd get this from your rate limiting configuration
        return {
            'requests_per_minute': 60,
            'requests_per_hour': 1000,
            'burst_limit': 10
        }
    
    def _get_auth_requirements(self, endpoint: str) -> Dict[str, Any]:
        """Get authentication requirements for endpoint."""
        # This is a simplified implementation
        # In production, you'd get this from your authentication configuration
        public_endpoints = [
            '/api/v1/system/health/',
            '/api/v1/system/quick-health/',
            '/api/v1/auth/login/',
            '/api/v1/auth/register/'
        ]
        
        if endpoint in public_endpoints:
            return {
                'required': False,
                'type': 'none'
            }
        else:
            return {
                'required': True,
                'type': 'bearer_token',
                'scopes': ['read', 'write']
            }


class APIResponseMiddleware:
    """
    Middleware for standardizing API responses.
    """
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.standardizer = APIStandardizer()
    
    def __call__(self, request):
        # Add request ID
        request.request_id = self._generate_request_id()
        
        # Record start time
        request.start_time = time.time()
        
        response = self.get_response(request)
        
        # Standardize response if it's an API endpoint
        if self._is_api_endpoint(request):
            response = self._standardize_response(request, response)
        
        return response
    
    def _is_api_endpoint(self, request) -> bool:
        """Check if request is for an API endpoint."""
        return request.path.startswith('/api/')
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _standardize_response(self, request, response) -> HttpResponse:
        """Standardize API response."""
        try:
            # If response is already a JsonResponse, standardize it
            if isinstance(response, JsonResponse):
                data = json.loads(response.content)
                
                # Check if already standardized
                if 'status' in data and 'timestamp' in data:
                    return response
                
                # Standardize the response
                api_response = self.standardizer.success_response(
                    data=data,
                    request_id=request.request_id
                )
                
                # Add performance metrics
                api_response = self.standardizer.add_performance_metrics(
                    api_response, request.start_time
                )
                
                return self.standardizer.to_json_response(api_response, response.status_code)
            
            return response
            
        except Exception as e:
            logger.error(f"Error standardizing response: {e}")
            return response


# Global instance
api_standardizer = APIStandardizer() 