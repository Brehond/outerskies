# Outer Skies API Documentation

## Overview

The Outer Skies API provides comprehensive astrology chart generation and interpretation services. This RESTful API uses JWT authentication and follows standard HTTP status codes.

## Base URL

```
https://your-domain.com/api/v1/
```

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

## Rate Limiting

- **Anonymous users**: 100 requests/hour
- **Authenticated users**: 1000 requests/hour
- **Chart generation**: 10 requests/hour
- **AI interpretation**: 50 requests/hour

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  }
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description",
  "data": {
    // Error details here
  }
}
```

## Endpoints

### Authentication

#### Register User
```http
POST /api/v1/auth/register/
```

**Request Body:**
```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword123",
  "password_confirm": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com",
      "first_name": "John",
      "last_name": "Doe"
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
  }
}
```

#### Login User
```http
POST /api/v1/auth/login/
```

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "data": {
    "user": {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com"
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
    }
  }
}
```

#### Refresh Token
```http
POST /api/v1/auth/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

#### Logout User
```http
POST /api/v1/auth/logout/
```

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### User Management

#### Get User Profile
```http
GET /api/v1/users/profile/
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "status": "success",
  "message": "Profile retrieved successfully",
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "birth_date": "1990-05-15",
    "birth_time": "14:30:00",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timezone": "America/New_York",
    "preferred_zodiac_type": "tropical",
    "preferred_house_system": "placidus",
    "preferred_ai_model": "gpt-4",
    "is_premium": false,
    "charts_count": 5,
    "subscription_status": {
      "plan_name": "Free Plan",
      "status": "active",
      "is_active": true,
      "charts_remaining": 2,
      "interpretations_remaining": 3
    }
  }
}
```

#### Update User Profile
```http
PATCH /api/v1/users/update_profile/
```

**Request Body:**
```json
{
  "first_name": "Updated",
  "last_name": "Name",
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timezone": "America/New_York"
}
```

#### Change Password
```http
POST /api/v1/users/change_password/
```

**Request Body:**
```json
{
  "old_password": "currentpassword",
  "new_password": "newpassword123"
}
```

### Chart Management

#### Generate Chart
```http
POST /api/v1/charts/generate/
```

**Request Body:**
```json
{
  "birth_date": "1990-05-15",
  "birth_time": "14:30:00",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "location_name": "New York, NY",
  "timezone": "America/New_York",
  "zodiac_type": "tropical",
  "house_system": "placidus",
  "ai_model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 1000,
  "interpretation_type": "comprehensive",
  "chart_name": "My Birth Chart"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Chart generated successfully",
  "data": {
    "chart": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "My Birth Chart",
      "birth_date": "1990-05-15",
      "birth_time": "14:30:00",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "location_name": "New York, NY",
      "timezone": "America/New_York",
      "zodiac_type": "tropical",
      "house_system": "placidus",
      "ai_model_used": "gpt-4",
      "planetary_positions": {
        "Sun": {"sign": "Taurus", "degree": 24.5},
        "Moon": {"sign": "Cancer", "degree": 12.3}
      },
      "house_positions": {
        "ascendant": {"sign": "Libra", "degree": 15.2}
      },
      "interpretation": "Your birth chart reveals a strong Taurean influence...",
      "interpretation_tokens_used": 850,
      "interpretation_cost": 0.023,
      "created_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

#### List User Charts
```http
GET /api/v1/charts/
```

**Response:**
```json
{
  "status": "success",
  "message": "Charts retrieved successfully",
  "data": {
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "My Birth Chart",
        "birth_date": "1990-05-15",
        "chart_summary": "Sun: Taurus, Moon: Cancer, Asc: Libra",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

#### Get Chart Details
```http
GET /api/v1/charts/{chart_id}/
```

#### Generate Chart Interpretation
```http
POST /api/v1/charts/{chart_id}/interpret/
```

**Request Body:**
```json
{
  "ai_model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 1000,
  "interpretation_type": "comprehensive"
}
```

### Subscription Management

#### List Subscription Plans
```http
GET /api/v1/subscriptions/
```

**Response:**
```json
{
  "status": "success",
  "message": "Subscription plans retrieved successfully",
  "data": {
    "count": 3,
    "results": [
      {
        "id": 1,
        "name": "Free Plan",
        "plan_type": "free",
        "billing_cycle": "monthly",
        "price_monthly": 0,
        "price_yearly": 0,
        "charts_per_month": 3,
        "ai_interpretations_per_month": 3,
        "description": "Basic features for new users",
        "features": ["Basic chart generation", "Limited AI interpretations"]
      },
      {
        "id": 2,
        "name": "Stellar Plan",
        "plan_type": "stellar",
        "billing_cycle": "monthly",
        "price_monthly": 9.99,
        "price_yearly": 99.99,
        "charts_per_month": 25,
        "ai_interpretations_per_month": 25,
        "description": "Enhanced features for astrology enthusiasts",
        "features": ["Advanced chart generation", "More AI interpretations", "Chart history"]
      }
    ]
  }
}
```

#### Get User Subscription
```http
GET /api/v1/subscriptions/my_subscription/
```

### Payment Management

#### List Payment History
```http
GET /api/v1/payments/
```

### Coupon Validation

#### Validate Coupon
```http
POST /api/v1/coupons/validate/
```

**Request Body:**
```json
{
  "code": "WELCOME20"
}
```

### System Information

#### Health Check
```http
GET /api/v1/system/health/
```

**Response:**
```json
{
  "status": "success",
  "message": "System is healthy",
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0"
  }
}
```

#### List AI Models
```http
GET /api/v1/system/ai_models/
```

**Response:**
```json
{
  "status": "success",
  "message": "AI models retrieved successfully",
  "data": {
    "models": [
      {
        "name": "GPT-4",
        "id": "gpt-4",
        "max_tokens": 8192,
        "temperature": 0.7,
        "description": "Most capable GPT model"
      },
      {
        "name": "Claude-3 Opus",
        "id": "claude-3-opus",
        "max_tokens": 4096,
        "temperature": 0.7,
        "description": "Anthropic's most powerful model"
      }
    ]
  }
}
```

#### List Themes
```http
GET /api/v1/system/themes/
```

**Response:**
```json
{
  "status": "success",
  "message": "Themes retrieved successfully",
  "data": {
    "themes": [
      {
        "name": "Cosmic Night",
        "id": "cosmic-night",
        "description": "Deep space theme with stars and nebulas"
      },
      {
        "name": "Solar Flare",
        "id": "solar-flare",
        "description": "Bright and energetic solar theme"
      }
    ]
  }
}
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input data |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## Common Error Responses

### Validation Error
```json
{
  "status": "error",
  "message": "Invalid input data",
  "data": {
    "birth_date": ["This field is required."],
    "latitude": ["Ensure this value is less than or equal to 90."]
  }
}
```

### Authentication Error
```json
{
  "status": "error",
  "message": "Authentication credentials were not provided",
  "data": {}
}
```

### Rate Limit Error
```json
{
  "status": "error",
  "message": "Rate limit exceeded",
  "data": {
    "retry_after": 3600
  }
}
```

## SDKs and Libraries

### Python
```python
import requests

class OuterSkiesAPI:
    def __init__(self, base_url, access_token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def generate_chart(self, birth_data):
        url = f"{self.base_url}/charts/generate/"
        response = requests.post(url, json=birth_data, headers=self.headers)
        return response.json()
```

### JavaScript
```javascript
class OuterSkiesAPI {
    constructor(baseUrl, accessToken) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async generateChart(birthData) {
        const response = await fetch(`${this.baseUrl}/charts/generate/`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify(birthData)
        });
        return response.json();
    }
}
```

## Support

For API support and questions:
- Email: api-support@outerskies.com
- Documentation: https://docs.outerskies.com
- Status Page: https://status.outerskies.com
