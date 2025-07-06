# Comprehensive Testing Guide for Outer Skies

## Overview
This guide covers comprehensive testing for the Outer Skies astrology application, including unit tests, integration tests, security tests, and manual testing procedures.

## Test Categories

### 1. Unit Tests
- **Models**: Test data validation, relationships, and business logic
- **Views**: Test request handling, authentication, and responses
- **Forms**: Test form validation and data processing
- **Utilities**: Test helper functions and external integrations

### 2. Integration Tests
- **Payment Flow**: Complete subscription and payment processes
- **User Authentication**: Registration, login, password reset flows
- **Chart Generation**: End-to-end chart creation and processing
- **Plugin System**: Plugin loading, registration, and functionality

### 3. Security Tests
- **Authentication**: User access control and session management
- **Authorization**: Permission checks and data isolation
- **Input Validation**: XSS, CSRF, and injection prevention
- **Payment Security**: Stripe integration security

### 4. Performance Tests
- **Database Queries**: Query optimization and N+1 prevention
- **API Response Times**: Endpoint performance under load
- **Memory Usage**: Resource consumption monitoring

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-django pytest-cov

# Set up test environment
export DJANGO_SETTINGS_MODULE=astrology_ai.settings
export STRIPE_SECRET_KEY=sk_test_dummy
export STRIPE_PUBLISHABLE_KEY=pk_test_dummy
export STRIPE_WEBHOOK_SECRET=whsec_dummy
```

### Running All Tests
```bash
# Run all tests with coverage
python manage.py test --verbosity=2 --coverage

# Run specific app tests
python manage.py test payments --verbosity=2
python manage.py test chart --verbosity=2

# Run specific test classes
python manage.py test payments.tests.PaymentModelTests
python manage.py test chart.tests.test_auth.TestAuthFlow
```

### Running Tests with pytest
```bash
# Install pytest
pip install pytest pytest-django pytest-cov

# Run with pytest
pytest --cov=. --cov-report=html

# Run specific test file
pytest payments/tests.py -v

# Run with parallel execution
pytest -n auto
```

## Test Coverage Areas

### Payment System Tests (`payments/tests.py`)

#### Model Tests
- ✅ SubscriptionPlan creation and validation
- ✅ UserSubscription lifecycle management
- ✅ Payment record creation and tracking
- ✅ Coupon validation and usage tracking
- ✅ Coupon expiration and usage limits

#### View Tests
- ✅ Pricing page accessibility
- ✅ Subscription management access control
- ✅ Payment history display
- ✅ Subscription creation success/failure
- ✅ Subscription cancellation
- ✅ Coupon validation endpoints

#### Stripe Integration Tests
- ✅ Customer creation success/failure
- ✅ Subscription creation and management
- ✅ Payment processing
- ✅ Webhook handling
- ✅ Error handling for Stripe API failures

#### Security Tests
- ✅ CSRF protection on payment endpoints
- ✅ Authentication requirements
- ✅ User data isolation
- ✅ Webhook signature validation
- ✅ Input validation and sanitization

#### Edge Case Tests
- ✅ Inactive plan subscription attempts
- ✅ Duplicate subscription prevention
- ✅ Expired coupon usage
- ✅ Max coupon usage exceeded
- ✅ Concurrent subscription creation
- ✅ Subscription cancellation edge cases

### Authentication Tests (`chart/tests/test_auth.py`)

#### User Management
- ✅ User registration with validation
- ✅ Login/logout functionality
- ✅ Password change and reset
- ✅ Profile updates
- ✅ Duplicate username/email prevention

#### Security Features
- ✅ Password strength validation
- ✅ Session management
- ✅ Account lockout mechanisms
- ✅ Password reset token security

### Chart System Tests (`chart/tests/`)

#### Chart Creation
- ✅ Birth data validation
- ✅ Chart calculation accuracy
- ✅ Chart storage and retrieval
- ✅ Chart sharing and privacy settings

#### API Endpoints
- ✅ Chart generation API
- ✅ Chart retrieval API
- ✅ User chart history
- ✅ Chart deletion and management

### Plugin System Tests

#### Plugin Loading
- ✅ Plugin discovery and registration
- ✅ Plugin configuration validation
- ✅ Plugin dependency resolution
- ✅ Plugin activation/deactivation

#### Plugin Functionality
- ✅ Theme switcher functionality
- ✅ Astrology chat integration
- ✅ Custom plugin features
- ✅ Plugin error handling

## Manual Testing Checklist

### User Registration Flow
- [ ] User can register with valid data
- [ ] Validation errors display correctly
- [ ] Email verification works (if enabled)
- [ ] Duplicate username/email prevention
- [ ] Password strength requirements enforced

### User Login Flow
- [ ] Login with valid credentials
- [ ] Login with invalid credentials
- [ ] Remember me functionality
- [ ] Password reset flow
- [ ] Account lockout after failed attempts

### Chart Creation Flow
- [ ] Birth data input validation
- [ ] Chart generation accuracy
- [ ] Chart display and formatting
- [ ] Chart saving and retrieval
- [ ] Chart sharing settings

### Payment Flow
- [ ] Pricing page displays correctly
- [ ] Plan selection and comparison
- [ ] Stripe Elements integration
- [ ] Payment processing success
- [ ] Payment processing failure handling
- [ ] Subscription management
- [ ] Payment history display
- [ ] Coupon application and validation

### Admin Interface
- [ ] User management
- [ ] Subscription plan management
- [ ] Payment monitoring
- [ ] Coupon management
- [ ] System statistics

## Performance Testing

### Load Testing
```bash
# Install locust for load testing
pip install locust

# Run load test
locust -f load_tests.py --host=http://localhost:8000
```

### Database Performance
```bash
# Check slow queries
python manage.py dbshell
# Enable slow query log in MySQL/PostgreSQL

# Analyze query performance
python manage.py shell
from django.db import connection
from django.test.utils import override_settings
```

### Memory Profiling
```bash
# Install memory profiler
pip install memory-profiler

# Profile specific functions
python -m memory_profiler manage.py shell
```

## Security Testing

### Vulnerability Scanning
```bash
# Install security testing tools
pip install bandit safety

# Run security checks
bandit -r .
safety check
```

### Penetration Testing
- [ ] SQL injection testing
- [ ] XSS vulnerability testing
- [ ] CSRF protection testing
- [ ] Authentication bypass testing
- [ ] Authorization testing
- [ ] Input validation testing

## Continuous Integration

### GitHub Actions Setup
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov
      - name: Run tests
        run: |
          python manage.py test --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Test Data Management

### Fixtures
```bash
# Create test data fixtures
python manage.py dumpdata --indent=2 > fixtures/test_data.json

# Load test data
python manage.py loaddata fixtures/test_data.json
```

### Factory Classes
```python
# payments/factories.py
import factory
from payments.models import SubscriptionPlan, Coupon

class SubscriptionPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SubscriptionPlan
    
    name = factory.Sequence(lambda n: f'Plan {n}')
    price = factory.Faker('pydecimal', left_digits=2, right_digits=2)
    interval = 'month'
    is_active = True
```

## Monitoring and Alerting

### Test Metrics
- Test coverage percentage
- Test execution time
- Failed test count
- Security vulnerability count
- Performance regression detection

### Alerting
- Failed test notifications
- Coverage drop alerts
- Security vulnerability alerts
- Performance degradation alerts

## Best Practices

### Test Organization
1. **Arrange**: Set up test data and conditions
2. **Act**: Execute the code being tested
3. **Assert**: Verify the expected outcomes

### Test Naming
- Use descriptive test names
- Follow the pattern: `test_<scenario>_<expected_behavior>`
- Group related tests in test classes

### Test Isolation
- Each test should be independent
- Use `setUp()` and `tearDown()` methods
- Mock external dependencies
- Use test databases

### Test Data
- Use factories for test data creation
- Keep test data minimal and focused
- Use realistic but safe test data
- Clean up test data after tests

### Performance Considerations
- Mock expensive operations
- Use database transactions for rollback
- Avoid unnecessary database queries
- Use appropriate test settings

## Troubleshooting

### Common Issues
1. **Database connection errors**: Check test database configuration
2. **Import errors**: Verify test dependencies are installed
3. **Mock failures**: Check mock setup and expectations
4. **Test isolation issues**: Ensure proper cleanup in tearDown

### Debugging Tests
```bash
# Run tests with debug output
python manage.py test --verbosity=3

# Run specific test with pdb
python -m pytest payments/tests.py::PaymentModelTests::test_subscription_plan_creation -s --pdb

# Check test database
python manage.py dbshell --database=test
```

## Next Steps

1. **Automate Testing**: Set up CI/CD pipeline
2. **Expand Coverage**: Add tests for edge cases
3. **Performance Testing**: Implement load testing
4. **Security Testing**: Regular security audits
5. **Monitoring**: Set up test metrics and alerting

This comprehensive testing approach ensures the Outer Skies application is robust, secure, and ready for production deployment. 