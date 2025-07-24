"""
Centralized Exception System for Outer Skies

This module provides a standardized exception hierarchy for consistent
error handling across the application.
"""

from typing import Dict, Any, Optional


class OuterSkiesException(Exception):
    """
    Base exception class for all Outer Skies exceptions.
    Provides standardized error handling with error codes and details.
    """
    
    def __init__(self, message: str, error_code: str, status_code: int = 500, 
                 details: Optional[Dict[str, Any]] = None, user_message: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.user_message = user_message or message
        super().__init__(self.message)


# Authentication & Authorization Exceptions
class AuthenticationError(OuterSkiesException):
    """Raised when authentication fails."""
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_FAILED", 401, details)


class AuthorizationError(OuterSkiesException):
    """Raised when user lacks permission for an action."""
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_FAILED", 403, details)


class TokenExpiredError(AuthenticationError):
    """Raised when JWT token has expired."""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, {"token_type": "jwt", "reason": "expired"})


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, {"token_type": "jwt", "reason": "invalid"})


# Validation Exceptions
class ValidationError(OuterSkiesException):
    """Raised when input validation fails."""
    def __init__(self, message: str = "Validation failed", field_errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, {"field_errors": field_errors})


class InvalidCoordinateError(ValidationError):
    """Raised when coordinate values are invalid."""
    def __init__(self, coordinate_type: str, value: float):
        message = f"Invalid {coordinate_type}: {value}"
        details = {"coordinate_type": coordinate_type, "value": value}
        super().__init__(message, details)


class InvalidBirthDateError(ValidationError):
    """Raised when birth date is invalid."""
    def __init__(self, birth_date: str):
        message = f"Invalid birth date: {birth_date}"
        details = {"birth_date": birth_date}
        super().__init__(message, details)


# Business Logic Exceptions
class ChartGenerationError(OuterSkiesException):
    """Raised when chart generation fails."""
    def __init__(self, message: str = "Chart generation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CHART_GENERATION_FAILED", 500, details)


class AIInterpretationError(OuterSkiesException):
    """Raised when AI interpretation fails."""
    def __init__(self, message: str = "AI interpretation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AI_INTERPRETATION_FAILED", 500, details)


class EphemerisCalculationError(OuterSkiesException):
    """Raised when ephemeris calculations fail."""
    def __init__(self, message: str = "Ephemeris calculation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EPHEMERIS_CALCULATION_FAILED", 500, details)


# Resource Exceptions
class ResourceNotFoundError(OuterSkiesException):
    """Raised when a requested resource is not found."""
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} not found: {resource_id}"
        details = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, "RESOURCE_NOT_FOUND", 404, details)


class ChartNotFoundError(ResourceNotFoundError):
    """Raised when a chart is not found."""
    def __init__(self, chart_id: str):
        super().__init__("Chart", chart_id)


class UserNotFoundError(ResourceNotFoundError):
    """Raised when a user is not found."""
    def __init__(self, user_id: str):
        super().__init__("User", user_id)


# Rate Limiting Exceptions
class RateLimitExceededError(OuterSkiesException):
    """Raised when rate limit is exceeded."""
    def __init__(self, limit_type: str, limit: int, window: int, retry_after: int = 3600):
        message = f"Rate limit exceeded for {limit_type}"
        details = {
            "limit_type": limit_type,
            "limit": limit,
            "window": window,
            "retry_after": retry_after
        }
        super().__init__(message, "RATE_LIMIT_EXCEEDED", 429, details)


# External Service Exceptions
class ExternalServiceError(OuterSkiesException):
    """Raised when external service calls fail."""
    def __init__(self, service_name: str, message: str = "External service error", 
                 details: Optional[Dict[str, Any]] = None):
        full_message = f"{service_name}: {message}"
        service_details = {"service_name": service_name}
        if details:
            service_details.update(details)
        super().__init__(full_message, "EXTERNAL_SERVICE_ERROR", 503, service_details)


class OpenRouterAPIError(ExternalServiceError):
    """Raised when OpenRouter API calls fail."""
    def __init__(self, message: str = "OpenRouter API error", details: Optional[Dict[str, Any]] = None):
        super().__init__("OpenRouter API", message, details)


class StripeAPIError(ExternalServiceError):
    """Raised when Stripe API calls fail."""
    def __init__(self, message: str = "Stripe API error", details: Optional[Dict[str, Any]] = None):
        super().__init__("Stripe API", message, details)


# Database Exceptions
class DatabaseError(OuterSkiesException):
    """Raised when database operations fail."""
    def __init__(self, message: str = "Database operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", 500, details)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message, {"error_type": "connection"})


class DatabaseTimeoutError(DatabaseError):
    """Raised when database operation times out."""
    def __init__(self, message: str = "Database operation timed out"):
        super().__init__(message, {"error_type": "timeout"})


# Task Processing Exceptions
class TaskProcessingError(OuterSkiesException):
    """Raised when background task processing fails."""
    def __init__(self, task_type: str, message: str = "Task processing failed", 
                 details: Optional[Dict[str, Any]] = None):
        full_message = f"{task_type} task failed: {message}"
        task_details = {"task_type": task_type}
        if details:
            task_details.update(details)
        super().__init__(full_message, "TASK_PROCESSING_ERROR", 500, task_details)


class TaskTimeoutError(TaskProcessingError):
    """Raised when a task times out."""
    def __init__(self, task_type: str, timeout_seconds: int):
        message = f"Task timed out after {timeout_seconds} seconds"
        details = {"timeout_seconds": timeout_seconds}
        super().__init__(task_type, message, details)


class TaskCancelledError(TaskProcessingError):
    """Raised when a task is cancelled."""
    def __init__(self, task_type: str):
        super().__init__(task_type, "Task was cancelled", {"cancelled": True})


# Configuration Exceptions
class ConfigurationError(OuterSkiesException):
    """Raised when there's a configuration issue."""
    def __init__(self, message: str = "Configuration error", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", 500, details)


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when a required environment variable is missing."""
    def __init__(self, variable_name: str):
        message = f"Missing required environment variable: {variable_name}"
        details = {"variable_name": variable_name}
        super().__init__(message, details)


# Security Exceptions
class SecurityError(OuterSkiesException):
    """Raised when security violations are detected."""
    def __init__(self, message: str = "Security violation detected", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SECURITY_ERROR", 403, details)


class IPBlockedError(SecurityError):
    """Raised when an IP address is blocked."""
    def __init__(self, ip_address: str, reason: str = "IP address is blocked"):
        message = f"IP address {ip_address} is blocked"
        details = {"ip_address": ip_address, "reason": reason}
        super().__init__(message, details)


class SuspiciousActivityError(SecurityError):
    """Raised when suspicious activity is detected."""
    def __init__(self, activity_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"Suspicious activity detected: {activity_type}"
        activity_details = {"activity_type": activity_type}
        if details:
            activity_details.update(details)
        super().__init__(message, activity_details)


# Utility function to convert Django exceptions to OuterSkies exceptions
def convert_django_exception(django_exception: Exception) -> OuterSkiesException:
    """Convert Django exceptions to OuterSkies exceptions."""
    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.http import Http404
    from django.core.exceptions import PermissionDenied
    
    if isinstance(django_exception, DjangoValidationError):
        return ValidationError("Validation failed", getattr(django_exception, 'message_dict', {}))
    elif isinstance(django_exception, Http404):
        return ResourceNotFoundError("Resource", "unknown")
    elif isinstance(django_exception, PermissionDenied):
        return AuthorizationError("Access denied")
    else:
        return OuterSkiesException(
            str(django_exception),
            "UNKNOWN_ERROR",
            500,
            {"original_exception": type(django_exception).__name__}
        ) 