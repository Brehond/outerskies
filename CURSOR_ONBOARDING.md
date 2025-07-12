# Outer Skies: Cursor Pro Onboarding & Team Guide

---

## Table of Contents
1. [Living Document Rules & Policies](#living-document-rules--policies)
2. [Quick Start & Project Overview](#quick-start--project-overview)
3. [Key Project Structure](#key-project-structure)
4. [Development & Testing Guidelines](#development--testing-guidelines)
5. [Current Status & Roadmap](#current-status--roadmap)
6. [Historical Log & Archived Updates](#historical-log--archived-updates)

---

## 1. Living Document Rules & Policies

### Document Preservation Policy
- **NEVER remove or overwrite existing content** – This is a living document that accumulates knowledge.
- **ALWAYS append new information** to relevant sections or create new sections with timestamps.
- **Preserve all historical context** – Previous decisions, debugging steps, and solutions are valuable.
- **Use chronological timestamps** for all new additions (e.g., "🆕 June 2025: New Feature").
- **Cross-reference related sections** when adding new information.

### Testing Requirements & Output Capture System
- **ALL tests must implement text file output capture** for debugging and analysis.
- **Create timestamped output files** (e.g., `test_results_20250625_143022.txt`).
- **Implement automatic failure checking** – parse output files to detect and report failures.
- **Capture both success and failure outputs** for comprehensive debugging.
- **Use consistent naming convention**: `{test_name}_results_{timestamp}.txt`.
- **Include test metadata**: timestamp, test duration, success/failure count, error details.
- **Store outputs in a dedicated directory** (e.g., `test_outputs/` or `logs/`).

### Development Workflow Requirements
- **Document all major decisions** in this file with rationale and context.
- **Record debugging steps** and solutions for future reference.
- **Update project status** after each significant change.
- **Maintain chronological development log** with timestamps.
- **Cross-reference related documentation** and external resources.

---

## 2. Quick Start & Project Overview

### Quick Start
1. **Clone the repository** and set up your Python virtual environment (see `README.md`).
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Copy environment variables:**
   ```sh
   cp env.example .env
   # Edit .env as needed, ensuring you have a valid OPENROUTER_API_KEY
   ```
4. **Run migrations:**
   ```sh
   python manage.py migrate
   ```
5. **Start the development server:**
   ```sh
   python manage.py runserver
   ```
6. **Access the app:**
   - Open [http://localhost:8000/chart/form/](http://localhost:8000/chart/form/) in your browser.

### Project Overview
Outer Skies is an astrology web application that combines traditional astrology calculations (using Swiss Ephemeris) with AI-powered interpretations. It uses Django, PostgreSQL, Tailwind CSS, Docker, and integrates with the OpenRouter API for AI features.

**Current Status:** ✅ **Production-Ready Core Infrastructure with Advanced Feature Development Underway**

#### Technology Stack
- **Backend**: Django 4.2+, Django REST Framework, Celery, Redis
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Tailwind CSS, Responsive Design
- **AI Integration**: OpenRouter API (GPT-4, Claude-3, etc.)
- **Authentication**: JWT, Custom security middleware stack
- **Payments**: Stripe integration
- **Monitoring**: Custom health checks, performance monitoring
- **Deployment**: Docker, Docker Compose

#### Key Applications
- `astrology_ai/` - Main Django project settings and configuration
- `chart/` - Core astrology logic, user management, chart generation
- `api/` - Comprehensive REST API with v1 endpoints
- `payments/` - Stripe-based subscription and payment system
- `plugins/` - Extensible plugin architecture
- `monitoring/` - Health checks and performance monitoring
- `ai_integration/` - OpenRouter API integration

---

## 3. Key Project Structure

- `astrology_ai/` – Django project settings, main URL configuration, and the theme context processor (`context_processors.py`).
- `chart/` – Core astrology logic, user auth, chart models, templates, and a comprehensive security middleware stack.
- `ai_integration/` – OpenRouter API and AI logic.
- `plugins/` – Extensible plugin system. The most important plugin is the `theme_switcher`.
- `ephemeris/` – Swiss Ephemeris data and binaries.
- `static/`, `templates/` – Frontend assets.
- `scripts/` – Utilities for testing and development.
- `monitoring/` – Health checks and performance monitoring.
- `payments/` – Stripe-based payment and subscription system.

#### Key Configuration Files
- `astrology_ai/settings.py` - Main Django configuration with Celery, Redis, security settings
- `astrology_ai/context_processors.py` - Theme system with 75+ color palettes
- `chart/celery_utils.py` - Background task utilities and fallback mechanisms
- `api/v1/views.py` - Complete REST API implementation
- `monitoring/health_checks.py` - System health monitoring (8 critical components)
- `docker-compose.yml` - Container orchestration
- `requirements.txt` - Python dependencies
- `package.json` - Node.js dependencies for Tailwind CSS

#### Security Infrastructure
- `chart/middleware/` - Comprehensive security middleware stack:
  - `EnhancedSecurityMiddleware` - Core security headers and protections
  - `RateLimitMiddleware` - API rate limiting
  - `APIAuthMiddleware` - API authentication
  - `RequestSigningMiddleware` - Request signature verification
  - `EncryptionMiddleware` - Data encryption
  - `SessionSecurityMiddleware` - Session management
  - `FileUploadSecurityMiddleware` - File upload security
  - `ErrorHandlingMiddleware` - Error handling and logging

---

## 4. Development & Testing Guidelines

### Code Quality Standards
- **Branching:** Use feature branches for new work, merge to `main` via PRs.
- **Commits:** Write clear, descriptive commit messages.
- **Testing:** Add/maintain tests for new features and bug fixes.
- **Plugins:** Follow the `PLUGIN_SYSTEM_GUIDE.md` for plugin development.
- **Security:** Review `SECURITY_AUDIT_REPORT.md` for best practices.
- **Code Quality:** All code passes flake8 linting with no whitespace issues.

### Testing Guidelines
- **Implement output capture** for all tests with timestamped files (see [Testing Requirements & Output Capture System](#testing-requirements--output-capture-system)).
- **Use comprehensive test suites** with automatic failure detection.
- **Test both success and failure scenarios**.
- **Validate API responses** and error handling.
- **Test background task functionality** in both Celery and fallback modes.
- **Include performance metrics** in test outputs.
- **Integration Testing:** Test API endpoints, background tasks, and database operations.

### Debugging Tools
- Use debug scripts in `scripts/` directory for troubleshooting.
- Check logs for detailed error information.
- Use health check endpoints for system status.
- Monitor performance metrics for bottlenecks.

### Documentation Standards
- **Update this file** with all significant changes and decisions.
- **Preserve historical context** – never remove existing information.
- **Use timestamps** for all new additions.
- **Cross-reference related sections** and external documentation.
- **Include debugging steps** and solutions for future reference.

---

## 5. Current Status & Roadmap

### Completed Phases
- User Authentication System
- Plugin System Foundation
- Security Infrastructure
- Theming System (75+ themes)
- Core Feature Performance (caching)
- REST API (with documentation and testing)
- Background Task Processing (Celery + fallback)
- Monitoring & Observability (health checks, performance monitoring)

### Current Phase
- AI Chart Interpretation: Continue to expand and refine AI integration for chart readings.
- User Dashboard: Improve user experience and chart management.
- Payment Integration: Finalize and test payment flows.

### Next Phases
- Plugin Marketplace: Enable third-party plugin discovery and installation.
- Mobile Responsiveness: Polish UI for mobile devices.
- Documentation: Continue improving onboarding and dev docs.
- Advanced Features: Transit calculations, compatibility charts.

---

## 6. Historical Log & Archived Updates

**The full update and log history has been moved to a separate file for clarity and maintainability.**

- Please see `ONBOARDING_HISTORY_LOG.txt` in the project root for the complete chronological record of all phase logs, changelogs, and historical updates.
- This file will continue to reference the canonical onboarding and testing policies above.
- All new historical entries should be appended to `ONBOARDING_HISTORY_LOG.txt` with timestamps and context.

---

🆕 July 2025: Comprehensive Code Quality Improvements and Linter Compliance

- **Achieved 100% linter compliance**: Successfully resolved all flake8 linting errors across the entire codebase, including whitespace issues, import organization, and code style violations.
- **Fixed null byte corruption issues**: Identified and resolved null byte corruption in several `__init__.py` files within the plugins directory that were causing syntax errors and preventing proper module imports.
- **Enhanced plugin system stability**: Cleaned up and standardized all plugin files (`aspect_generator`, `house_generator`, `theme_switcher`, `astrology_chat`) to ensure consistent code quality and proper functionality.
- **Improved testing infrastructure**: Updated test files to follow consistent formatting standards and removed any linting violations that could interfere with test execution.
- **Code cleanup automation**: Created and executed multiple cleanup scripts (`final_cleanup.py`, `surgical_fix.py`, `fix_linter_issues.py`) to systematically address code quality issues across the entire project.
- **Security validation**: Confirmed that all sensitive data remains properly secured in environment variables with no hardcoded secrets or API keys in the codebase.
- **Documentation updates**: Updated README.md and CURSOR_ONBOARDING.md to reflect current project state, including new features, testing procedures, and development guidelines.
- **Outcome**: The codebase is now production-ready with:
  - Zero linter errors or warnings
  - Consistent code formatting across all files
  - Proper module imports and syntax
  - Enhanced plugin system reliability
  - Comprehensive testing coverage
  - Updated documentation reflecting current capabilities

🆕 July 2025: Debugging & Fixes for Master Chart Interpretation and House Cusps

- **Resolved a persistent TypeError** (`unsupported operand type(s) for +: 'float' and 'str'`) that prevented master chart interpretations from rendering. The error was traced to the construction of the `ascendant` and `midheaven` fields in the master prompt data, especially when house cusp calculations failed or returned malformed data.
- **Improved robustness of master prompt data construction**: Now, all values (especially those derived from house cusps and ascendant) are type-checked and safely converted to strings, preventing float+str errors even when house data is missing or invalid.
- **Enhanced logging**: Added detailed logging to capture the types and values of all master prompt data fields, which helped pinpoint the source of the error.
- **Rate limit debugging**: Provided guidance and commands to clear the Django cache and reset the rate limit during development/testing, ensuring smoother local testing workflows.
- **Server management**: Demonstrated how to safely stop, restart, and clear the cache for the Django development server as part of the debugging process.
- **Outcome**: The master chart interpretation now renders correctly, even when house cusp data is missing or invalid, and the system is more robust against malformed ephemeris data.

🆕 July 2025: House Position Calculation System Overhaul & Plugin Integration Fixes

- **Fixed Swiss Ephemeris API usage for house position calculations**: Resolved critical issues with `swe.house_pos` function calls that were causing all planets to display in the 1st house regardless of their actual positions. The correct API signature was identified and implemented: `swe.house_pos(armc, lat, eps, [longitude, latitude], hs_code)` where `hs_code` is a byte string (e.g., `b'P'` for Placidus).
- **Corrected house system mapping**: Updated the house system mapping to use consistent byte string codes (`b'P'` for Placidus, `b'W'` for Whole Sign) across both `swe.houses` and `swe.house_pos` function calls.
- **Fixed plugin data format mismatches**: Resolved critical data format inconsistencies between the main chart generation system and the plugin system. The main system returns `chart_data['planetary_positions']` and `chart_data['house_cusps']`, but plugins were expecting `chart_data['positions']` and `chart_data['houses']`. Updated both `aspect_generator` and `house_generator` plugins to use the correct data keys.
- **Enhanced house position calculation robustness**: Improved error handling and fallback mechanisms for house position calculations, including better validation of house cusps data and manual house calculation when `swe.house_pos` fails.
- **Comprehensive cache clearing system**: Created multiple cache clearing scripts to address different caching layers:
  - `clear_cache.py` - Clears all Django cache
  - `clear_ai_cache.py` - Clears AI interpretation cache specifically
  - `clear_session_cache.py` - Clears Django session cache and session data from database
- **Added debugging infrastructure**: Implemented detailed logging throughout the house position calculation pipeline to track:
  - House cusp calculations and validation
  - Individual planet house position calculations
  - Data format transformations between systems
  - Cache hit/miss patterns
- **Fixed aspect integration**: Ensured that aspect calculations properly integrate with the corrected house position system, allowing aspects to reference accurate house placements in interpretations.
- **Outcome**: Planetary house positions now display correctly across all systems:
  - Master chart interpretations show varied house positions (e.g., Sun in 6th house, Moon in 8th house, etc.)
  - Individual planet interpretations use correct house positions
  - Plugin system (aspect_generator, house_generator) works with accurate house data
  - No more "all planets in 1st house" display issues
- **Testing validation**: Created `test_house_positions.py` script to validate house position calculations independently and ensure the Swiss Ephemeris API integration works correctly.
- **Cross-system compatibility**: Ensured that the fixed house position system works consistently across:
  - Main chart generation views (`chart/views.py`)
  - Plugin system (`plugins/aspect_generator/`, `plugins/house_generator/`)
  - Background task processing (`chart/tasks.py`)
  - API endpoints (`api/v1/views.py`)

_Cross-reference: See also ONBOARDING_HISTORY_LOG.txt for the full chronological log of all debugging and development sessions._

🆕 July 2025: Phase 1 Production Deployment, Docker, and CI/CD Test Success

- **All Phase 1 production deployment, Docker, and CI/CD tests now pass with 100% success rate.**
- **Key infrastructure improvements:**
  - Dockerfile now uses a multi-stage build, includes all required security and optimization steps, and passes all integration/security tests.
  - Development and production Docker Compose files are fully aligned with test requirements, including Redis and proper service configuration.
  - GitHub Actions workflow (`.github/workflows/deploy.yml`) is now robust, YAML-standards-compliant, and passes all structure/step tests (see [Testing Requirements & Output Capture System](#testing-requirements--output-capture-system)).
  - Environment variable templates and scripts (`env.production.example`, `scripts/deploy.sh`, `scripts/backup.sh`) are comprehensive and validated by automated tests.
  - Security audit and documentation files are up-to-date and referenced in the test suite.
- **Testing system:**
  - Comprehensive test runner (`run_comprehensive_tests.py`) covers Docker, deployment, CI/CD, environment, and security.
  - All test outputs are captured and timestamped for traceability (see [Testing Requirements & Output Capture System](#testing-requirements--output-capture-system)).
- **Next steps:**
  - Proceed with production deployment, following the recommendations in the test summary and [README.md].
  - For historical details, see `ONBOARDING_HISTORY_LOG.txt` and the test output files in `logs/` or `test_outputs/`. 