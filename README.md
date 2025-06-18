# 🌌 Outer Skies

AI-powered astrology chart reader using:
- 🐍 Django + REST Framework
- 🪐 Swiss Ephemeris
- 🤖 OpenRouter AI API
- 💳 Stripe subscriptions
- 🐘 PostgreSQL

## 🚀 Features
- Modular AI interpretations for each planet
- Stripe checkout + webhook handling
- Chart calculation via Swiss Ephemeris
- Full-stack ready for production

## 🛠 Setup

## Overview
A Django-based astrology chart generation and interpretation application.

## Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Brehond/outerskies.git
cd outerskies
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root with the following variables:
```
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=your_database_url
STRIPE_API_KEY=your_stripe_api_key
```

### 5. Run Migrations
```bash
python manage.py migrate
```

### 6. Start the Development Server
```bash
python manage.py runserver
```

### 7. Access the Application
Open your browser and go to `http://127.0.0.1:8000/`.

## Additional Notes
- **Admin Access:** Create a superuser with `python manage.py createsuperuser`.
- **Testing:** Run tests with `python manage.py test`.

### Docker Setup
```bash
docker-compose up --build
```

# Trigger CI build

```bash
git clone https://github.com/YOUR-USERNAME/outer-skies.git
cd outer-skies
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```
