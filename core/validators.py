"""
Comprehensive Input Validation System for Outer Skies

This module provides robust input validation to prevent security vulnerabilities
and ensure data integrity across the application.
"""

import re
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, EmailValidator
from django.utils.translation import gettext_lazy as _

from .exceptions import ValidationError as OuterSkiesValidationError, InvalidCoordinateError, InvalidBirthDateError


class BaseValidator:
    """Base class for all validators."""
    
    def __init__(self, field_name: str = None):
        self.field_name = field_name
    
    def validate(self, value: Any) -> Any:
        """Validate and return cleaned value."""
        raise NotImplementedError
    
    def __call__(self, value: Any) -> Any:
        """Make validator callable."""
        return self.validate(value)


class StringValidator(BaseValidator):
    """Validate and sanitize string inputs."""
    
    def __init__(self, max_length: int = None, min_length: int = None, 
                 allowed_chars: str = None, strip_whitespace: bool = True,
                 field_name: str = None):
        super().__init__(field_name)
        self.max_length = max_length
        self.min_length = min_length
        self.allowed_chars = allowed_chars
        self.strip_whitespace = strip_whitespace
    
    def validate(self, value: Any) -> str:
        """Validate string input."""
        if value is None:
            return ""
        
        # Convert to string
        if not isinstance(value, str):
            value = str(value)
        
        # Strip whitespace if requested
        if self.strip_whitespace:
            value = value.strip()
        
        # Check length constraints
        if self.min_length and len(value) < self.min_length:
            raise OuterSkiesValidationError(
                f"String too short. Minimum length: {self.min_length}",
                {"field": self.field_name, "min_length": self.min_length, "actual_length": len(value)}
            )
        
        if self.max_length and len(value) > self.max_length:
            raise OuterSkiesValidationError(
                f"String too long. Maximum length: {self.max_length}",
                {"field": self.field_name, "max_length": self.max_length, "actual_length": len(value)}
            )
        
        # Check allowed characters
        if self.allowed_chars:
            invalid_chars = [char for char in value if char not in self.allowed_chars]
            if invalid_chars:
                raise OuterSkiesValidationError(
                    f"Invalid characters found: {invalid_chars}",
                    {"field": self.field_name, "invalid_chars": invalid_chars}
                )
        
        return value


class EmailFieldValidator(BaseValidator):
    """Validate email addresses."""
    
    def __init__(self, field_name: str = None):
        super().__init__(field_name)
        self.django_validator = EmailValidator()
    
    def validate(self, value: Any) -> str:
        """Validate email address."""
        if not value:
            raise OuterSkiesValidationError(
                "Email is required",
                {"field": self.field_name}
            )
        
        value = str(value).strip().lower()
        
        try:
            self.django_validator(value)
        except ValidationError:
            raise OuterSkiesValidationError(
                "Invalid email format",
                {"field": self.field_name, "value": value}
            )
        
        return value


class CoordinateValidator(BaseValidator):
    """Validate coordinate values."""
    
    def __init__(self, coordinate_type: str = "coordinate", field_name: str = None):
        super().__init__(field_name)
        self.coordinate_type = coordinate_type
    
    def validate(self, value: Any) -> Decimal:
        """Validate coordinate value."""
        if value is None:
            raise OuterSkiesValidationError(
                f"{self.coordinate_type.capitalize()} is required",
                {"field": self.field_name}
            )
        
        try:
            # Convert to Decimal for precise validation
            decimal_value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            raise OuterSkiesValidationError(
                f"Invalid {self.coordinate_type} format",
                {"field": self.field_name, "value": value}
            )
        
        # Validate latitude range (-90 to 90)
        if self.coordinate_type == "latitude" and not -90 <= decimal_value <= 90:
            raise InvalidCoordinateError("latitude", float(decimal_value))
        
        # Validate longitude range (-180 to 180)
        if self.coordinate_type == "longitude" and not -180 <= decimal_value <= 180:
            raise InvalidCoordinateError("longitude", float(decimal_value))
        
        return decimal_value


class DateValidator(BaseValidator):
    """Validate date inputs."""
    
    def __init__(self, allow_future: bool = False, min_date: date = None, 
                 max_date: date = None, field_name: str = None):
        super().__init__(field_name)
        self.allow_future = allow_future
        self.min_date = min_date
        self.max_date = max_date
    
    def validate(self, value: Any) -> date:
        """Validate date input."""
        if value is None:
            raise OuterSkiesValidationError(
                "Date is required",
                {"field": self.field_name}
            )
        
        # Convert string to date if needed
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise OuterSkiesValidationError(
                    "Invalid date format. Use YYYY-MM-DD",
                    {"field": self.field_name, "value": value}
                )
        elif isinstance(value, datetime):
            value = value.date()
        elif not isinstance(value, date):
            raise OuterSkiesValidationError(
                "Invalid date type",
                {"field": self.field_name, "value": value}
            )
        
        # Check future date constraint
        if not self.allow_future and value > date.today():
            raise InvalidBirthDateError(str(value))
        
        # Check min/max date constraints
        if self.min_date and value < self.min_date:
            raise OuterSkiesValidationError(
                f"Date too early. Minimum date: {self.min_date}",
                {"field": self.field_name, "min_date": self.min_date, "value": value}
            )
        
        if self.max_date and value > self.max_date:
            raise OuterSkiesValidationError(
                f"Date too late. Maximum date: {self.max_date}",
                {"field": self.field_name, "max_date": self.max_date, "value": value}
            )
        
        return value


class TimeValidator(BaseValidator):
    """Validate time inputs."""
    
    def __init__(self, field_name: str = None):
        super().__init__(field_name)
    
    def validate(self, value: Any) -> str:
        """Validate time input."""
        if value is None:
            raise OuterSkiesValidationError(
                "Time is required",
                {"field": self.field_name}
            )
        
        # Convert to string if needed
        if not isinstance(value, str):
            value = str(value)
        
        # Validate time format (HH:MM)
        time_pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
        if not re.match(time_pattern, value):
            raise OuterSkiesValidationError(
                "Invalid time format. Use HH:MM (24-hour)",
                {"field": self.field_name, "value": value}
            )
        
        return value


class IntegerValidator(BaseValidator):
    """Validate integer inputs."""
    
    def __init__(self, min_value: int = None, max_value: int = None, 
                 field_name: str = None):
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any) -> int:
        """Validate integer input."""
        if value is None:
            raise OuterSkiesValidationError(
                "Integer value is required",
                {"field": self.field_name}
            )
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise OuterSkiesValidationError(
                "Invalid integer format",
                {"field": self.field_name, "value": value}
            )
        
        # Check range constraints
        if self.min_value is not None and int_value < self.min_value:
            raise OuterSkiesValidationError(
                f"Value too small. Minimum: {self.min_value}",
                {"field": self.field_name, "min_value": self.min_value, "value": int_value}
            )
        
        if self.max_value is not None and int_value > self.max_value:
            raise OuterSkiesValidationError(
                f"Value too large. Maximum: {self.max_value}",
                {"field": self.field_name, "max_value": self.max_value, "value": int_value}
            )
        
        return int_value


class DecimalValidator(BaseValidator):
    """Validate decimal inputs."""
    
    def __init__(self, min_value: Decimal = None, max_value: Decimal = None,
                 decimal_places: int = None, field_name: str = None):
        super().__init__(field_name)
        self.min_value = min_value
        self.max_value = max_value
        self.decimal_places = decimal_places
    
    def validate(self, value: Any) -> Decimal:
        """Validate decimal input."""
        if value is None:
            raise OuterSkiesValidationError(
                "Decimal value is required",
                {"field": self.field_name}
            )
        
        try:
            decimal_value = Decimal(str(value))
        except (ValueError, InvalidOperation):
            raise OuterSkiesValidationError(
                "Invalid decimal format",
                {"field": self.field_name, "value": value}
            )
        
        # Check range constraints
        if self.min_value is not None and decimal_value < self.min_value:
            raise OuterSkiesValidationError(
                f"Value too small. Minimum: {self.min_value}",
                {"field": self.field_name, "min_value": self.min_value, "value": decimal_value}
            )
        
        if self.max_value is not None and decimal_value > self.max_value:
            raise OuterSkiesValidationError(
                f"Value too large. Maximum: {self.max_value}",
                {"field": self.field_name, "max_value": self.max_value, "value": decimal_value}
            )
        
        # Check decimal places
        if self.decimal_places is not None:
            decimal_str = str(decimal_value)
            if '.' in decimal_str:
                places = len(decimal_str.split('.')[1])
                if places > self.decimal_places:
                    raise OuterSkiesValidationError(
                        f"Too many decimal places. Maximum: {self.decimal_places}",
                        {"field": self.field_name, "decimal_places": places, "max_places": self.decimal_places}
                    )
        
        return decimal_value


class JSONValidator(BaseValidator):
    """Validate JSON inputs."""
    
    def __init__(self, schema: Dict = None, required_keys: List[str] = None,
                 allowed_keys: List[str] = None, field_name: str = None):
        super().__init__(field_name)
        self.schema = schema
        self.required_keys = required_keys or []
        self.allowed_keys = allowed_keys
    
    def validate(self, value: Any) -> Dict:
        """Validate JSON input."""
        if value is None:
            return {}
        
        # Parse JSON if string
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise OuterSkiesValidationError(
                    "Invalid JSON format",
                    {"field": self.field_name, "value": value}
                )
        
        # Ensure it's a dictionary
        if not isinstance(value, dict):
            raise OuterSkiesValidationError(
                "Value must be a dictionary",
                {"field": self.field_name, "value": value}
            )
        
        # Check required keys
        missing_keys = [key for key in self.required_keys if key not in value]
        if missing_keys:
            raise OuterSkiesValidationError(
                f"Missing required keys: {missing_keys}",
                {"field": self.field_name, "missing_keys": missing_keys}
            )
        
        # Check allowed keys
        if self.allowed_keys:
            invalid_keys = [key for key in value.keys() if key not in self.allowed_keys]
            if invalid_keys:
                raise OuterSkiesValidationError(
                    f"Invalid keys: {invalid_keys}",
                    {"field": self.field_name, "invalid_keys": invalid_keys, "allowed_keys": self.allowed_keys}
                )
        
        return value


class URLFieldValidator(BaseValidator):
    """Validate URL inputs."""
    
    def __init__(self, allowed_schemes: List[str] = None, field_name: str = None):
        super().__init__(field_name)
        self.allowed_schemes = allowed_schemes or ['http', 'https']
        self.django_validator = URLValidator(schemes=self.allowed_schemes)
    
    def validate(self, value: Any) -> str:
        """Validate URL input."""
        if not value:
            raise OuterSkiesValidationError(
                "URL is required",
                {"field": self.field_name}
            )
        
        value = str(value).strip()
        
        try:
            self.django_validator(value)
        except ValidationError:
            raise OuterSkiesValidationError(
                "Invalid URL format",
                {"field": self.field_name, "value": value}
            )
        
        return value


class ChoiceValidator(BaseValidator):
    """Validate choice inputs."""
    
    def __init__(self, choices: List[Any], field_name: str = None):
        super().__init__(field_name)
        self.choices = choices
    
    def validate(self, value: Any) -> Any:
        """Validate choice input."""
        if value is None:
            raise OuterSkiesValidationError(
                "Choice value is required",
                {"field": self.field_name}
            )
        
        if value not in self.choices:
            raise OuterSkiesValidationError(
                f"Invalid choice. Allowed values: {self.choices}",
                {"field": self.field_name, "value": value, "allowed_choices": self.choices}
            )
        
        return value


class ListValidator(BaseValidator):
    """Validate list inputs."""
    
    def __init__(self, item_validator: BaseValidator = None, min_length: int = None,
                 max_length: int = None, field_name: str = None):
        super().__init__(field_name)
        self.item_validator = item_validator
        self.min_length = min_length
        self.max_length = max_length
    
    def validate(self, value: Any) -> List:
        """Validate list input."""
        if value is None:
            return []
        
        # Convert to list if needed
        if not isinstance(value, list):
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    raise OuterSkiesValidationError(
                        "Invalid list format",
                        {"field": self.field_name, "value": value}
                    )
            else:
                value = [value]
        
        # Check length constraints
        if self.min_length and len(value) < self.min_length:
            raise OuterSkiesValidationError(
                f"List too short. Minimum length: {self.min_length}",
                {"field": self.field_name, "min_length": self.min_length, "actual_length": len(value)}
            )
        
        if self.max_length and len(value) > self.max_length:
            raise OuterSkiesValidationError(
                f"List too long. Maximum length: {self.max_length}",
                {"field": self.field_name, "max_length": self.max_length, "actual_length": len(value)}
            )
        
        # Validate items if validator provided
        if self.item_validator:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = self.item_validator.validate(item)
                    validated_items.append(validated_item)
                except OuterSkiesValidationError as e:
                    raise OuterSkiesValidationError(
                        f"Invalid item at index {i}: {e.message}",
                        {"field": self.field_name, "index": i, "item_error": e.details}
                    )
            return validated_items
        
        return value


# Predefined validators for common use cases
class Validators:
    """Collection of predefined validators."""
    
    # String validators
    STRING_VALIDATOR = StringValidator()  # Generic string validator
    USERNAME = StringValidator(min_length=3, max_length=150, allowed_chars="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    PASSWORD = StringValidator(min_length=8, max_length=128)
    EMAIL = EmailFieldValidator()  # Fixed: use EmailFieldValidator instead of EmailValidator
    NAME = StringValidator(min_length=1, max_length=100)
    LOCATION = StringValidator(max_length=255)
    TIMEZONE = StringValidator(max_length=50)
    
    # Coordinate validators
    LATITUDE = CoordinateValidator("latitude")
    LONGITUDE = CoordinateValidator("longitude")
    
    # Date/time validators
    BIRTH_DATE = DateValidator(allow_future=False)
    BIRTH_TIME = TimeValidator()
    
    # Numeric validators
    POSITIVE_INTEGER = IntegerValidator(min_value=0)
    PERCENTAGE = IntegerValidator(min_value=0, max_value=100)
    POSITIVE_DECIMAL = DecimalValidator(min_value=Decimal('0'))
    COST = DecimalValidator(min_value=Decimal('0'), decimal_places=6)
    
    # Choice validators
    ZODIAC_TYPE = ChoiceValidator(['tropical', 'sidereal'])
    HOUSE_SYSTEM = ChoiceValidator(['placidus', 'whole_sign'])
    
    # List validators
    TAGS = ListValidator(StringValidator(max_length=50), max_length=20)
    
    # JSON validators
    CHART_DATA = JSONValidator()
    PLANETARY_POSITIONS = JSONValidator()
    HOUSE_POSITIONS = JSONValidator()
    ASPECTS = JSONValidator()
    
    # Factory methods for dynamic validators
    @staticmethod
    def CHOICE_VALIDATOR(choices):
        """Create a choice validator with specific choices."""
        return ChoiceValidator(choices)
    
    @staticmethod
    def STRING_VALIDATOR_WITH_LENGTH(min_length=None, max_length=None):
        """Create a string validator with specific length constraints."""
        return StringValidator(min_length=min_length, max_length=max_length)


# Validation decorator for views
def validate_input(validators: Dict[str, BaseValidator]):
    """Decorator to validate view inputs."""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            # Validate request data
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.data if hasattr(request, 'data') else request.POST
                validated_data = {}
                
                for field_name, validator in validators.items():
                    if field_name in data:
                        try:
                            validated_data[field_name] = validator.validate(data[field_name])
                        except OuterSkiesValidationError as e:
                            return handle_validation_error({field_name: e.details})
                
                # Add validated data to request
                request.validated_data = validated_data
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


# Utility function for validation
def validate_chart_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate chart generation data."""
    validators = {
        'birth_date': Validators.BIRTH_DATE,
        'birth_time': Validators.BIRTH_TIME,
        'latitude': Validators.LATITUDE,
        'longitude': Validators.LONGITUDE,
        'location_name': Validators.LOCATION,
        'timezone': Validators.TIMEZONE,
        'zodiac_type': Validators.ZODIAC_TYPE,
        'house_system': Validators.HOUSE_SYSTEM,
    }
    
    validated_data = {}
    field_errors = {}
    
    for field_name, validator in validators.items():
        if field_name in data:
            try:
                validated_data[field_name] = validator.validate(data[field_name])
            except OuterSkiesValidationError as e:
                field_errors[field_name] = e.details
    
    if field_errors:
        raise OuterSkiesValidationError("Chart data validation failed", field_errors)
    
    return validated_data 