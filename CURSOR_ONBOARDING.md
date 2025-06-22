# Outer Skies: Cursor Pro Onboarding & Team Guide

Welcome to the Outer Skies project! This document is designed for new team members and Cursor Pro chat instances to quickly get up to speed and collaborate effectively.

---

## 🚀 Project Overview
Outer Skies is an astrology web application that combines traditional astrology calculations (using Swiss Ephemeris) with AI-powered interpretations. It uses Django, PostgreSQL, Tailwind CSS, Docker, and integrates with the OpenRouter API for AI features.

---

## ⚡ Quick Start for Cursor Pro
1. **Clone the repository** and set up your Python virtual environment (see `README.md`).
2. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Copy environment variables:**
   ```sh
   cp env.example .env
   # Edit .env as needed
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
   - Open [http://localhost:8000/](http://localhost:8000/) in your browser.

---

## 🗂️ Key Project Structure
- `astrology_ai/` – Django project settings
- `chart/` – Core astrology logic, user auth, chart models, templates
- `ai_integration/` – OpenRouter API and AI logic
- `plugins/` – Plugin system for extensibility
- `ephemeris/` – Swiss Ephemeris data and binaries
- `static/`, `templates/` – Frontend assets
- `scripts/` – Utilities for testing and development

---

## 🤖 Using Cursor Pro with Outer Skies
- **Ask for code explanations, file summaries, or architecture diagrams.**
- **Request code edits, new features, or bug fixes.**
- **Run and debug tests, migrations, and server commands.**
- **Use the `CURSOR_ONBOARDING.md` as a reference for project context.**
- **Check `README.md` and `TEAM_SETUP_INSTRUCTIONS.md` for more details.**

---

## 🤝 Development & Collaboration Guidelines
- **Branching:** Use feature branches for new work, merge to `main` via PRs.
- **Commits:** Write clear, descriptive commit messages.
- **Testing:** Add/maintain tests for new features and bug fixes.
- **Plugins:** Follow the `PLUGIN_SYSTEM_GUIDE.md` for plugin development.
- **Security:** Review `SECURITY_AUDIT_REPORT.md` for best practices.

---

## 📈 Current & Next Phases of Development
### Current Phase
- User authentication, profile, and chart history (complete)
- Plugin system foundation (complete)
- Security and test coverage (in progress)

### Next Phases
- **AI Chart Interpretation:** Expand AI integration for chart readings
- **User Dashboard:** Improve user experience and chart management
- **Payment Integration:** Finalize and test payment flows
- **Plugin Marketplace:** Enable third-party plugin discovery and install
- **Mobile Responsiveness:** Polish UI for mobile devices
- **Documentation:** Continue improving onboarding and dev docs

---

## 🆘 Where to Ask Questions / Get Help
- Use the `README.md` and this file for quick answers
- For plugin development, see `PLUGIN_SYSTEM_GUIDE.md`
- For team setup, see `TEAM_SETUP_INSTRUCTIONS.md`
- For security, see `SECURITY_AUDIT_REPORT.md`
- Ask in team chat or open a GitHub issue for anything else

---

Welcome aboard, and happy hacking! 🌌 