"""
Enhanced Input Validation System

This module provides comprehensive input validation with security considerations,
consistent error handling, and support for various data types.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Union, Tuple
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, URLValidator
from django.utils.translation import gettext_lazy as _
from datetime import datetime, date
import pytz

logger = logging.getLogger('input_validator')


class InputValidator:
    """
    Comprehensive input validator with security considerations.
    """
    
    # Validation patterns
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?1?\d{9,15}$',
        'username': r'^[a-zA-Z0-9_]{3,30}$',
        'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{12,}$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'date': r'^\d{4}-\d{2}-\d{2}$',
        'time': r'^\d{2}:\d{2}(:\d{2})?$',
        'latitude': r'^-?([1-8]?[0-9](\.[0-9]+)?|90(\.0+)?)$',
        'longitude': r'^-?((1[0-7][0-9]|[1-9]?[0-9])(\.[0-9]+)?|180(\.0+)?)$',
        'zip_code': r'^\d{5}(-\d{4})?$',
        'url': r'^https?://[^\s/$.?#].[^\s]*$',
    }
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'onload=',
        r'onerror=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<form[^>]*>',
        r'<input[^>]*>',
        r'<textarea[^>]*>',
        r'<select[^>]*>',
        r'<button[^>]*>',
        r'<a[^>]*>',
        r'<img[^>]*>',
        r'<video[^>]*>',
        r'<audio[^>]*>',
        r'<source[^>]*>',
        r'<track[^>]*>',
        r'<canvas[^>]*>',
        r'<svg[^>]*>',
        r'<math[^>]*>',
        r'<details[^>]*>',
        r'<dialog[^>]*>',
        r'<menu[^>]*>',
        r'<menuitem[^>]*>',
        r'<summary[^>]*>',
        r'<content[^>]*>',
        r'<element[^>]*>',
        r'<shadow[^>]*>',
        r'<template[^>]*>',
        r'<slot[^>]*>',
        r'<picture[^>]*>',
        r'<figure[^>]*>',
        r'<figcaption[^>]*>',
        r'<main[^>]*>',
        r'<section[^>]*>',
        r'<article[^>]*>',
        r'<aside[^>]*>',
        r'<header[^>]*>',
        r'<footer[^>]*>',
        r'<nav[^>]*>',
        r'<hgroup[^>]*>',
        r'<address[^>]*>',
        r'<blockquote[^>]*>',
        r'<dd[^>]*>',
        r'<div[^>]*>',
        r'<dl[^>]*>',
        r'<dt[^>]*>',
        r'<fieldset[^>]*>',
        r'<figcaption[^>]*>',
        r'<figure[^>]*>',
        r'<hr[^>]*>',
        r'<li[^>]*>',
        r'<ol[^>]*>',
        r'<p[^>]*>',
        r'<pre[^>]*>',
        r'<ul[^>]*>',
        r'<abbr[^>]*>',
        r'<acronym[^>]*>',
        r'<b[^>]*>',
        r'<bdi[^>]*>',
        r'<bdo[^>]*>',
        r'<big[^>]*>',
        r'<cite[^>]*>',
        r'<code[^>]*>',
        r'<del[^>]*>',
        r'<dfn[^>]*>',
        r'<em[^>]*>',
        r'<i[^>]*>',
        r'<ins[^>]*>',
        r'<kbd[^>]*>',
        r'<mark[^>]*>',
        r'<meter[^>]*>',
        r'<progress[^>]*>',
        r'<q[^>]*>',
        r'<rp[^>]*>',
        r'<rt[^>]*>',
        r'<ruby[^>]*>',
        r'<s[^>]*>',
        r'<samp[^>]*>',
        r'<small[^>]*>',
        r'<strong[^>]*>',
        r'<sub[^>]*>',
        r'<sup[^>]*>',
        r'<time[^>]*>',
        r'<tt[^>]*>',
        r'<u[^>]*>',
        r'<var[^>]*>',
        r'<wbr[^>]*>',
    ]
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r'(\%27)|(\')|(\-\-)|(\%23)|(#)',
        r'((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))',
        r'((\%27)|(\'))union',
        r'exec(\s|\+)+(s|x)p\w+',
        r'((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))',
        r'((\%27)|(\'))((\%61)|a|(\%41))((\%6E)|n|(\%4E))((\%64)|d|(\%44))',
        r'((\%27)|(\'))((\%69)|i|(\%49))((\%6E)|n|(\%4E))((\%73)|s|(\%53))((\%65)|e|(\%45))((\%72)|r|(\%52))',
        r'((\%27)|(\'))((\%64)|d|(\%44))((\%72)|r|(\%52))((\%6F)|o|(\%4F))((\%70)|p|(\%50))',
        r'((\%27)|(\'))((\%75)|u|(\%55))((\%70)|p|(\%50))((\%64)|d|(\%44))((\%61)|a|(\%41))((\%74)|t|(\%54))((\%65)|e|(\%45))',
        r'((\%27)|(\'))((\%64)|d|(\%44))((\%65)|e|(\%45))((\%6C)|l|(\%4C))((\%65)|e|(\%45))((\%74)|t|(\%54))((\%65)|e|(\%45))',
    ]
    
    @classmethod
    def validate_data(cls, data: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Validate data against a schema and return cleaned data and errors.
        
        Args:
            data: Input data to validate
            schema: Validation schema defining rules for each field
            
        Returns:
            Tuple of (cleaned_data, errors)
        """
        cleaned_data = {}
        errors = []
        
        for field_name, field_schema in schema.items():
            field_value = data.get(field_name)
            
            # Check if field is required
            if field_schema.get('required', False) and field_value is None:
                errors.append(f"{field_name}: This field is required")
                continue
            
            # Skip validation if field is None and not required
            if field_value is None:
                cleaned_data[field_name] = None
                continue
            
            # Validate field
            try:
                validated_value = cls._validate_field(field_name, field_value, field_schema)
                cleaned_data[field_name] = validated_value
            except ValidationError as e:
                errors.extend([f"{field_name}: {error}" for error in e.messages])
            except Exception as e:
                errors.append(f"{field_name}: Validation failed - {str(e)}")
        
        return cleaned_data, errors
    
    @classmethod
    def _validate_field(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> Any:
        """
        Validate a single field according to its schema.
        """
        field_type = schema.get('type', 'string')
        
        # Check for dangerous content first
        if isinstance(value, str):
            cls._check_dangerous_content(field_name, value)
        
        # Type-specific validation
        if field_type == 'string':
            return cls._validate_string(field_name, value, schema)
        elif field_type == 'email':
            return cls._validate_email(field_name, value, schema)
        elif field_type == 'url':
            return cls._validate_url(field_name, value, schema)
        elif field_type == 'integer':
            return cls._validate_integer(field_name, value, schema)
        elif field_type == 'float':
            return cls._validate_float(field_name, value, schema)
        elif field_type == 'boolean':
            return cls._validate_boolean(field_name, value, schema)
        elif field_type == 'date':
            return cls._validate_date(field_name, value, schema)
        elif field_type == 'datetime':
            return cls._validate_datetime(field_name, value, schema)
        elif field_type == 'list':
            return cls._validate_list(field_name, value, schema)
        elif field_type == 'dict':
            return cls._validate_dict(field_name, value, schema)
        elif field_type == 'uuid':
            return cls._validate_uuid(field_name, value, schema)
        elif field_type == 'latitude':
            return cls._validate_latitude(field_name, value, schema)
        elif field_type == 'longitude':
            return cls._validate_longitude(field_name, value, schema)
        else:
            raise ValidationError(f"Unknown field type: {field_type}")
    
    @classmethod
    def _check_dangerous_content(cls, field_name: str, value: str):
        """
        Check for dangerous content in string values.
        """
        value_lower = value.lower()
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f'Dangerous content detected in field {field_name}: {pattern}')
                raise ValidationError(f'Dangerous content detected in {field_name}')
        
        # Check for SQL injection patterns
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                logger.warning(f'SQL injection attempt detected in field {field_name}: {pattern}')
                raise ValidationError(f'Invalid content in {field_name}')
        
        # Check for null bytes
        if '\x00' in value:
            logger.warning(f'Null bytes detected in field {field_name}')
            raise ValidationError(f'Invalid content in {field_name}')
    
    @classmethod
    def _validate_string(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> str:
        """Validate string field."""
        if not isinstance(value, str):
            raise ValidationError(f'{field_name} must be a string')
        
        # Check length constraints
        min_length = schema.get('min_length')
        max_length = schema.get('max_length')
        
        if min_length and len(value) < min_length:
            raise ValidationError(f'{field_name} must be at least {min_length} characters long')
        
        if max_length and len(value) > max_length:
            raise ValidationError(f'{field_name} must be no more than {max_length} characters long')
        
        # Check pattern
        pattern = schema.get('pattern')
        if pattern and not re.match(pattern, value):
            raise ValidationError(f'{field_name} format is invalid')
        
        # Trim whitespace if specified
        if schema.get('trim', True):
            value = value.strip()
        
        return value
    
    @classmethod
    def _validate_email(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> str:
        """Validate email field."""
        if not isinstance(value, str):
            raise ValidationError(f'{field_name} must be a string')
        
        value = value.strip().lower()
        
        # Check pattern
        if not re.match(cls.PATTERNS['email'], value):
            raise ValidationError(f'{field_name} must be a valid email address')
        
        # Use Django's email validator
        try:
            validate_email(value)
        except ValidationError:
            raise ValidationError(f'{field_name} must be a valid email address')
        
        return value
    
    @classmethod
    def _validate_url(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> str:
        """Validate URL field."""
        if not isinstance(value, str):
            raise ValidationError(f'{field_name} must be a string')
        
        value = value.strip()
        
        # Use Django's URL validator
        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise ValidationError(f'{field_name} must be a valid URL')
        
        return value
    
    @classmethod
    def _validate_integer(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> int:
        """Validate integer field."""
        try:
            if isinstance(value, str):
                value = int(value)
            elif not isinstance(value, int):
                raise ValidationError(f'{field_name} must be an integer')
        except (ValueError, TypeError):
            raise ValidationError(f'{field_name} must be an integer')
        
        # Check range constraints
        min_value = schema.get('min_value')
        max_value = schema.get('max_value')
        
        if min_value is not None and value < min_value:
            raise ValidationError(f'{field_name} must be at least {min_value}')
        
        if max_value is not None and value > max_value:
            raise ValidationError(f'{field_name} must be no more than {max_value}')
        
        return value
    
    @classmethod
    def _validate_float(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> float:
        """Validate float field."""
        try:
            if isinstance(value, str):
                value = float(value)
            elif not isinstance(value, (int, float)):
                raise ValidationError(f'{field_name} must be a number')
        except (ValueError, TypeError):
            raise ValidationError(f'{field_name} must be a number')
        
        # Check range constraints
        min_value = schema.get('min_value')
        max_value = schema.get('max_value')
        
        if min_value is not None and value < min_value:
            raise ValidationError(f'{field_name} must be at least {min_value}')
        
        if max_value is not None and value > max_value:
            raise ValidationError(f'{field_name} must be no more than {max_value}')
        
        return value
    
    @classmethod
    def _validate_boolean(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> bool:
        """Validate boolean field."""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', '1', 'yes', 'on'):
                return True
            elif value_lower in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValidationError(f'{field_name} must be a boolean value')
        elif isinstance(value, int):
            return bool(value)
        else:
            raise ValidationError(f'{field_name} must be a boolean value')
    
    @classmethod
    def _validate_date(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> date:
        """Validate date field."""
        if isinstance(value, date):
            return value
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                raise ValidationError(f'{field_name} must be a valid date (YYYY-MM-DD)')
        else:
            raise ValidationError(f'{field_name} must be a valid date')
    
    @classmethod
    def _validate_datetime(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> datetime:
        """Validate datetime field."""
        if isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            # Try common datetime formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            
            raise ValidationError(f'{field_name} must be a valid datetime')
        else:
            raise ValidationError(f'{field_name} must be a valid datetime')
    
    @classmethod
    def _validate_list(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> List:
        """Validate list field."""
        if not isinstance(value, list):
            raise ValidationError(f'{field_name} must be a list')
        
        # Check length constraints
        min_length = schema.get('min_length')
        max_length = schema.get('max_length')
        
        if min_length and len(value) < min_length:
            raise ValidationError(f'{field_name} must have at least {min_length} items')
        
        if max_length and len(value) > max_length:
            raise ValidationError(f'{field_name} must have no more than {max_length} items')
        
        # Validate items if schema provided
        item_schema = schema.get('items')
        if item_schema:
            validated_items = []
            for i, item in enumerate(value):
                try:
                    validated_item = cls._validate_field(f"{field_name}[{i}]", item, item_schema)
                    validated_items.append(validated_item)
                except ValidationError as e:
                    raise ValidationError(f'{field_name}[{i}]: {str(e)}')
            return validated_items
        
        return value
    
    @classmethod
    def _validate_dict(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> Dict:
        """Validate dict field."""
        if not isinstance(value, dict):
            raise ValidationError(f'{field_name} must be a dictionary')
        
        # Validate nested schema if provided
        properties = schema.get('properties')
        if properties:
            validated_dict = {}
            for key, item_schema in properties.items():
                if key in value:
                    try:
                        validated_dict[key] = cls._validate_field(f"{field_name}.{key}", value[key], item_schema)
                    except ValidationError as e:
                        raise ValidationError(f'{field_name}.{key}: {str(e)}')
            return validated_dict
        
        return value
    
    @classmethod
    def _validate_uuid(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> str:
        """Validate UUID field."""
        if isinstance(value, str):
            if not re.match(cls.PATTERNS['uuid'], value):
                raise ValidationError(f'{field_name} must be a valid UUID')
            return value
        else:
            raise ValidationError(f'{field_name} must be a valid UUID string')
    
    @classmethod
    def _validate_latitude(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> float:
        """Validate latitude field."""
        try:
            if isinstance(value, str):
                value = float(value)
            elif not isinstance(value, (int, float)):
                raise ValidationError(f'{field_name} must be a number')
        except (ValueError, TypeError):
            raise ValidationError(f'{field_name} must be a valid latitude')
        
        if not (-90 <= value <= 90):
            raise ValidationError(f'{field_name} must be between -90 and 90')
        
        return value
    
    @classmethod
    def _validate_longitude(cls, field_name: str, value: Any, schema: Dict[str, Any]) -> float:
        """Validate longitude field."""
        try:
            if isinstance(value, str):
                value = float(value)
            elif not isinstance(value, (int, float)):
                raise ValidationError(f'{field_name} must be a number')
        except (ValueError, TypeError):
            raise ValidationError(f'{field_name} must be a valid longitude')
        
        if not (-180 <= value <= 180):
            raise ValidationError(f'{field_name} must be between -180 and 180')
        
        return value


# Predefined validation schemas
VALIDATION_SCHEMAS = {
    'user_registration': {
        'username': {
            'type': 'string',
            'required': True,
            'min_length': 3,
            'max_length': 30,
            'pattern': InputValidator.PATTERNS['username']
        },
        'email': {
            'type': 'email',
            'required': True
        },
        'password': {
            'type': 'string',
            'required': True,
            'min_length': 12,
            'pattern': InputValidator.PATTERNS['password']
        },
        'first_name': {
            'type': 'string',
            'required': False,
            'max_length': 50
        },
        'last_name': {
            'type': 'string',
            'required': False,
            'max_length': 50
        }
    },
    
    'chart_generation': {
        'birth_date': {
            'type': 'date',
            'required': True
        },
        'birth_time': {
            'type': 'string',
            'required': True,
            'pattern': InputValidator.PATTERNS['time']
        },
        'latitude': {
            'type': 'latitude',
            'required': True
        },
        'longitude': {
            'type': 'longitude',
            'required': True
        },
        'location_name': {
            'type': 'string',
            'required': True,
            'max_length': 255
        },
        'timezone': {
            'type': 'string',
            'required': True,
            'max_length': 50
        },
        'zodiac_type': {
            'type': 'string',
            'required': True,
            'pattern': r'^(tropical|sidereal)$'
        },
        'house_system': {
            'type': 'string',
            'required': True,
            'pattern': r'^(placidus|whole_sign)$'
        },
        'ai_model': {
            'type': 'string',
            'required': True,
            'max_length': 50
        },
        'temperature': {
            'type': 'float',
            'required': True,
            'min_value': 0.0,
            'max_value': 1.0
        },
        'max_tokens': {
            'type': 'integer',
            'required': True,
            'min_value': 1,
            'max_value': 4000
        }
    }
}


# Utility functions
def validate_user_registration(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Validate user registration data."""
    return InputValidator.validate_data(data, VALIDATION_SCHEMAS['user_registration'])


def validate_chart_generation(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Validate chart generation data."""
    return InputValidator.validate_data(data, VALIDATION_SCHEMAS['chart_generation'])


def sanitize_input(value: Any) -> Any:
    """Sanitize input value to prevent XSS and other attacks."""
    if isinstance(value, str):
        # Remove null bytes
        value = value.replace('\x00', '')
        # Remove non-printable characters
        value = re.sub(r'[^\x20-\x7E]', '', value)
        # Basic HTML entity encoding
        value = value.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')
    elif isinstance(value, dict):
        return {k: sanitize_input(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_input(item) for item in value]
    
    return value 