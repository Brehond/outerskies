import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.http import Http404
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler for API responses
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the error response format
        if isinstance(response.data, dict):
            response.data = {
                'status': 'error',
                'message': response.data.get('detail', str(exc)),
                'data': None
            }
        else:
            response.data = {
                'status': 'error',
                'message': str(exc),
                'data': None
            }
    else:
        # Handle Django-specific exceptions
        if isinstance(exc, Http404):
            response = Response({
                'status': 'error',
                'message': _('Resource not found'),
                'data': None
            }, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, ValidationError):
            response = Response({
                'status': 'error',
                'message': _('Validation error'),
                'data': exc.message_dict if hasattr(exc, 'message_dict') else str(exc)
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Log unexpected exceptions
            logger.error(f"Unexpected exception in API: {exc}", exc_info=True)
            response = Response({
                'status': 'error',
                'message': _('Internal server error'),
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response


def api_response(data=None, message="Success", status_code=200, error=False):
    """
    Standardized API response helper
    """
    response_data = {
        'status': 'error' if error else 'success',
        'message': message,
        'data': data
    }

    return Response(response_data, status=status_code)


def success_response(data=None, message="Success"):
    """
    Helper for successful API responses
    """
    return api_response(data=data, message=message, status_code=200, error=False)


def error_response(message="Error", status_code=400, data=None):
    """
    Helper for error API responses
    """
    return api_response(data=data, message=message, status_code=status_code, error=True)


def paginated_response(queryset, serializer_class, request, page_size=20):
    """
    Helper for paginated responses
    """
    from rest_framework.pagination import PageNumberPagination
    from rest_framework import serializers

    paginator = PageNumberPagination()
    paginator.page_size = page_size

    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True)
    return Response(serializer.data)


def validate_required_fields(data, required_fields):
    """
    Validate that required fields are present in request data
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)

    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    return True 