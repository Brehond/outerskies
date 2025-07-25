# Outer Skies - AI-Powered Astrology Chart Analysis

Outer Skies is a modern web application that generates and interprets astrological birth charts using AI. The application combines traditional astrological calculations with advanced AI models to provide detailed, personalized interpretations.

## Features

- Birth chart calculation using Swiss Ephemeris
- AI-powered chart interpretation using OpenRouter API
- Support for multiple AI models (GPT-4, GPT-3.5-turbo, Claude-3, etc.)
- Modern, responsive UI built with Tailwind CSS
- Secure user authentication and data handling
- Rate limiting and API usage optimization
- Comprehensive logging and error tracking
- Extensible plugin system with multiple plugins
- Advanced security middleware stack
- Health monitoring and performance tracking
- Background task processing with Celery

## Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm
- Git
- PostgreSQL (for production)
- Redis (for caching and background tasks)

## Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Brehond/outerskies.git
   cd outer-skies
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Node.js Dependencies**
   ```bash
   npm install
   ```

4. **Configure Environment Variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize Database**
   ```bash
   python manage.py migrate
   ```

6. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

Visit http://127.0.0.1:8000 to access the application.

## Configuration

### Required Environment Variables

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to "False" in production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `STRIPE_*`: Stripe payment configuration (if using payments)

### Optional Environment Variables

- `DB_*`: Database configuration (defaults to SQLite)
- `SENTRY_DSN`: Sentry error tracking
- `LOG_LEVEL`: Logging level (defaults to INFO)
- `RATE_LIMIT_*`: Rate limiting configuration
- `REDIS_URL`: Redis connection URL (defaults to localhost)

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test categories
python run_comprehensive_tests.py
python test_production_deployment.py
```

### Code Quality
```bash
# Linting
flake8

# Auto-formatting
autopep8 --in-place --recursive .

# Security checks
python scripts/security_check.py
```

### Building CSS
```bash
npm run build
```

## Plugin System

Outer Skies includes an extensible plugin system with several built-in plugins:

- **Aspect Generator**: Generates aspect interpretations
- **House Generator**: Provides house-specific insights
- **Theme Switcher**: Dynamic theme management with 75+ color palettes
- **Astrology Chat**: AI-powered chat interface for astrological questions

See `PLUGIN_SYSTEM_GUIDE.md` for development guidelines.

## Production Deployment

For comprehensive production deployment instructions, see [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).

### Quick Production Setup

1. **Set Production Environment Variables**
   ```bash
   cp env.production.example .env.production
   # Edit .env.production with your actual values
   ```

2. **Using Production Docker Compose**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Using Deployment Script**
   ```bash
   # Linux/Mac
   ./scripts/deploy.sh
   
   # Windows
   scripts\deploy.bat
   ```

4. **Verify Deployment**
   ```bash
   curl -f http://localhost/health/
   curl -f http://localhost/api/v1/system/health/
   ```

### Production Features

- **SSL/HTTPS**: Automatic HTTP to HTTPS redirect
- **Security Headers**: Comprehensive security middleware
- **Rate Limiting**: API and endpoint rate limiting
- **Health Checks**: Multiple health check endpoints
- **Monitoring**: Sentry integration and performance monitoring
- **Backups**: Automated database backups with S3 support
- **Load Balancing**: Nginx reverse proxy with caching
- **Background Tasks**: Celery workers for async processing

## Security

- All sensitive data must be stored in environment variables
- Regular security audits are performed
- See `SECURITY_AUDIT_REPORT.md` for latest audit results
- Report security issues through GitHub Issues
- Comprehensive security middleware stack implemented

## Testing

The project includes comprehensive testing infrastructure:

- **Unit Tests**: Django test framework
- **Integration Tests**: API and database testing
- **Security Tests**: Authentication and authorization
- **Performance Tests**: Load and stress testing
- **Deployment Tests**: Docker and CI/CD validation

See `TESTING_GUIDE.md` and `COMPREHENSIVE_TESTING_SUMMARY.md` for detailed testing information.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: See README.md and CONTRIBUTING.md
- Issue Tracker: GitHub Issues
- Team Setup: See `CURSOR_ONBOARDING.md` for development team guidelines

## Acknowledgments

- Swiss Ephemeris for astronomical calculations
- OpenRouter for AI model access
- All contributors and maintainers
