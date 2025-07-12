from django.http import JsonResponse
from django.conf import settings
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger('security')


class DataValidationMiddleware:
    """
    Middleware for handling data validation of incoming requests.
    Supports both form data and JSON validation with schema checking.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Define validation schemas for different endpoints
        self.validation_schemas = {
            '/api/chart/': {
                'POST': {
                    'type': 'object',
                    'required': ['title', 'data'],
                    'properties': {
                        'title': {'type': 'string', 'minLength': 1, 'maxLength': 100},
                        'description': {'type': 'string', 'maxLength': 500},
                        'data': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['x', 'y'],
                                'properties': {
                                    'x': {'type': ['number', 'string']},
                                    'y': {'type': 'number'}
                                }
                            }
                        },
                        'options': {
                            'type': 'object',
                            'properties': {
                                'type': {'type': 'string', 'enum': ['line', 'bar', 'pie']},
                                'colors': {'type': 'array', 'items': {'type': 'string'}},
                                'showLegend': {'type': 'boolean'}
                            }
                        }
                    }
                }
            },
            '/api/data/': {
                'POST': {
                    'type': 'object',
                    'required': ['data'],
                    'properties': {
                        'data': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'required': ['value'],
                                'properties': {
                                    'value': {'type': 'number'},
                                    'timestamp': {'type': 'string', 'format': 'date-time'}
                                }
                            }
                        }
                    }
                }
            }
        }

        # Define sanitization rules
        self.sanitization_rules = {
            'string': {
                'strip_html': False,  # Don't strip HTML by default
                'max_length': 1000,
                'allowed_chars': None  # Allow all characters
            },
            'number': {
                'min_value': -1e9,
                'max_value': 1e9
            },
            'date': {
                'format': '%Y-%m-%dT%H:%M:%S.%fZ'
            }
        }

    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """Validate data against a JSON schema."""
        errors = []

        # Check required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in data:
                    errors.append(f"Missing required field: {field}")

        # Validate properties
        if 'properties' in schema:
            for field, value in data.items():
                if field in schema['properties']:
                    field_schema = schema['properties'][field]
                    field_errors = self._validate_field(value, field_schema, field)
                    errors.extend(field_errors)

        return errors

    def _validate_field(self, value: Any, schema: Dict[str, Any], field_name: str) -> List[str]:
        """Validate a single field against its schema."""
        errors = []

        # Type validation
        if 'type' in schema:
            if isinstance(schema['type'], list):
                if not any(self._check_type(value, t) for t in schema['type']):
                    errors.append(f"Field '{field_name}' must be one of types: {schema['type']}")
            elif not self._check_type(value, schema['type']):
                errors.append(f"Field '{field_name}' must be of type {schema['type']}")

        # String validation
        if schema.get('type') == 'string':
            if 'minLength' in schema and len(str(value)) < schema['minLength']:
                errors.append(f"Field '{field_name}' must be at least {schema['minLength']} characters")
            if 'maxLength' in schema and len(str(value)) > schema['maxLength']:
                errors.append(f"Field '{field_name}' must be at most {schema['maxLength']} characters")
            if 'enum' in schema and value not in schema['enum']:
                errors.append(f"Field '{field_name}' must be one of: {schema['enum']}")
            if 'format' in schema:
                try:
                    datetime.strptime(str(value), self.sanitization_rules['date']['format'])
                except ValueError:
                    errors.append(f"Field '{field_name}' must be a valid date in format {self.sanitization_rules['date']['format']}")

        # Number validation
        if schema.get('type') == 'number':
            try:
                if isinstance(value, str):
                    value = float(value)
                if not isinstance(value, (int, float)):
                    errors.append(f"Field '{field_name}' must be a valid number")
            except (ValueError, TypeError):
                errors.append(f"Field '{field_name}' must be a valid number")
            else:
                if 'minimum' in schema and value < schema['minimum']:
                    errors.append(f"Field '{field_name}' must be at least {schema['minimum']}")
                if 'maximum' in schema and value > schema['maximum']:
                    errors.append(f"Field '{field_name}' must be at most {schema['maximum']}")

        # Array validation
        if schema.get('type') == 'array':
            if 'items' in schema:
                for i, item in enumerate(value):
                    item_errors = self._validate_field(item, schema['items'], f"{field_name}[{i}]")
                    errors.extend(item_errors)

        # Object validation
        if schema.get('type') == 'object':
            if 'properties' in schema:
                for prop, prop_value in value.items():
                    if prop in schema['properties']:
                        prop_errors = self._validate_field(prop_value, schema['properties'][prop], f"{field_name}.{prop}")
                        errors.extend(prop_errors)

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected type."""
        if expected_type == 'string':
            return isinstance(value, str)
        elif expected_type == 'number':
            if isinstance(value, (int, float)):
                return True
            if isinstance(value, str):
                try:
                    float(value)
                    return True
                except (ValueError, TypeError):
                    return False
            return False
        elif expected_type == 'boolean':
            return isinstance(value, bool)
        elif expected_type == 'array':
            return isinstance(value, list)
        elif expected_type == 'object':
            return isinstance(value, dict)
        return False

    def _sanitize_value(self, value: Any, field_type: str) -> Any:
        """Sanitize a value based on its type."""
        rules = self.sanitization_rules.get(field_type, {})

        if field_type == 'string':
            value = str(value)
            if rules.get('strip_html'):
                # Only strip HTML tags, not the entire content
                value = re.sub(r'<[^>]+>', '', value)
            if rules.get('allowed_chars'):
                value = re.sub(rules['allowed_chars'], '', value)
            if rules.get('max_length'):
                value = value[:rules['max_length']]
            return value.strip()

        elif field_type == 'number':
            try:
                if isinstance(value, str):
                    value = float(value)
                if not isinstance(value, (int, float)):
                    return None
                if rules.get('min_value') is not None:
                    value = max(value, rules['min_value'])
                if rules.get('max_value') is not None:
                    value = min(value, rules['max_value'])
                return value
            except (ValueError, TypeError):
                return None

        elif field_type == 'date':
            try:
                if isinstance(value, str):
                    return datetime.strptime(value, rules['format'])
                return value
            except (ValueError, TypeError):
                return None

        return value

    def _sanitize_data(self, data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize all values in the data according to their schemas."""
        sanitized = {}

        if 'properties' in schema:
            for field, value in data.items():
                if field in schema['properties']:
                    field_schema = schema['properties'][field]
                    field_type = field_schema.get('type')

                    if isinstance(field_type, list):
                        field_type = field_type[0]  # Use first type for sanitization

                    if field_type == 'array' and 'items' in field_schema:
                        sanitized[field] = [
                            self._sanitize_data(item, field_schema['items'])
                            if isinstance(item, dict)
                            else self._sanitize_value(item, field_schema['items'].get('type', 'string'))
                            for item in value
                        ]
                    elif field_type == 'object' and 'properties' in field_schema:
                        sanitized[field] = self._sanitize_data(value, field_schema)
                    else:
                        sanitized[field] = self._sanitize_value(value, field_type)

        return sanitized

    def __call__(self, request):
        # Skip validation for non-API endpoints and GET requests
        if not request.path.startswith('/api/') or request.method == 'GET':
            return self.get_response(request)

        # Get validation schema for this endpoint and method
        schema = self.validation_schemas.get(request.path, {}).get(request.method)
        if not schema:
            return self.get_response(request)

        try:
            # Parse request data
            if request.headers.get('X-Encryption') == 'true':
                # Skip validation for encrypted requests
                return self.get_response(request)
            elif request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()

            # Validate data against schema
            errors = self._validate_schema(data, schema)
            if errors:
                logger.warning(f'Validation errors for {request.path}: {errors}')
                return JsonResponse({
                    'error': 'Validation failed',
                    'details': errors
                }, status=400)

            # Sanitize data
            sanitized_data = self._sanitize_data(data, schema)

            # Add sanitized data to request
            request.validated_data = sanitized_data

            return self.get_response(request)

        except json.JSONDecodeError:
            logger.error(f'Invalid JSON in request to {request.path}')
            return JsonResponse({
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f'Error processing request to {request.path}: {str(e)}')
            return JsonResponse({
                'error': 'Internal server error'
            }, status=500)
