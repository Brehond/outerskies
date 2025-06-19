# Contributing to Outer Skies

Thank you for your interest in contributing to Outer Skies! This document provides guidelines and instructions for contributing to the project.

## Getting Started

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/outer-skies.git
   cd outer-skies
   ```

2. **Set Up Development Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Install Node.js dependencies for Tailwind
   npm install
   ```

3. **Environment Variables**
   - Copy `env.example` to `.env`
   - Fill in all required environment variables
   - Never commit `.env` file or any sensitive credentials

## Development Workflow

1. **Create a New Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Code Style**
   - Follow PEP 8 guidelines for Python code
   - Use descriptive variable and function names
   - Add docstrings to functions and classes
   - Keep functions focused and single-purpose
   - Write clear commit messages

3. **Testing**
   - Write tests for new features
   - Run existing tests before submitting PR
   - Use `pytest` for running tests
   ```bash
   pytest
   ```

4. **Security Best Practices**
   - Never commit sensitive data (API keys, passwords)
   - Use environment variables for configuration
   - Follow security guidelines in settings.py
   - Run security checks before deployment

## Pull Request Process

1. **Before Submitting**
   - Update documentation if needed
   - Run all tests and ensure they pass
   - Update requirements.txt if new dependencies added
   - Remove any debug/print statements

2. **Submitting PR**
   - Create a clear PR title and description
   - Reference any related issues
   - Include screenshots for UI changes
   - List any breaking changes

3. **Code Review**
   - Address reviewer comments
   - Keep discussions focused and professional
   - Request re-review after making changes

## Project Structure

```
outer-skies/
├── ai_integration/      # AI model integration
├── astrology_ai/       # Django project settings
├── chart/             # Main chart generation app
│   ├── middleware/    # Custom middleware
│   ├── services/     # Business logic
│   └── templates/    # HTML templates
├── payments/         # Payment processing
└── scripts/         # Utility scripts
```

## Getting Help

- Check existing issues and documentation
- Ask questions in pull requests
- Contact maintainers for guidance

## License

By contributing, you agree that your contributions will be licensed under the project's license. 