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

## Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm
- Git
- PostgreSQL (for production)

## Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/outer-skies.git
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

## Development

### Running Tests
```bash
pytest
```

### Code Style
```bash
black .
flake8
```

### Building CSS
```bash
npm run build
```

## Production Deployment

1. **Set Production Environment Variables**
   - Set `DEBUG=False`
   - Configure secure `ALLOWED_HOSTS`
   - Set up PostgreSQL database
   - Configure Sentry for error tracking

2. **Using Docker**
   ```bash
   docker-compose up --build
   ```

3. **Manual Deployment**
   ```bash
   python manage.py collectstatic
   gunicorn astrology_ai.wsgi:application
   ```

## Security

- All sensitive data must be stored in environment variables
- Regular security audits are performed
- See SECURITY_AUDIT_REPORT.md for latest audit results
- Report security issues to security@outerskies.com

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [docs/](docs/)
- Issue Tracker: GitHub Issues
- Email: support@outerskies.com

## Acknowledgments

- Swiss Ephemeris for astronomical calculations
- OpenRouter for AI model access
- All contributors and maintainers
