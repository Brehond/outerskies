# 🚀 Outer Skies - Team Setup Instructions

## Prerequisites
- Python 3.11 or higher
- Node.js 18+ and npm
- Git

## Step-by-Step Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Brehond/outerskies
cd outer-skies
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies
```bash
npm install
```

### 4. Configure Environment Variables
```bash
# Copy the example environment file
cp env.example .env

# Edit .env file with your configuration
# Required variables:
# - SECRET_KEY (generate a random string)
# - OPENROUTER_API_KEY (get from https://openrouter.ai/)
```

### 5. Initialize Database
```bash
python manage.py migrate
```

### 6. Start the Development Server
```bash
python manage.py runserver
```

### 7. Access the Application
Open your browser and go to: http://127.0.0.1:8000

## Generating Your First Chart

### 1. Fill Out the Chart Form
- **Birth Date**: Enter your birth date
- **Birth Time**: Enter your birth time (as accurate as possible)
- **Location**: Enter your birth location (city, country)

### 2. Submit the Form
- Click "Generate Chart"
- The system will calculate planetary positions using Swiss Ephemeris
- AI will generate personalized interpretations for each planet

### 3. View Your Results
- Planetary positions and aspects
- Individual planet interpretations
- Master chart interpretation
- House positions and signs

## Example Chart Data
Try this test data:
- **Date**: July 21, 1993
- **Time**: 21:40 (9:40 PM)
- **Location**: Kentville, Canada

## Troubleshooting

### Common Issues:
1. **Port already in use**: Change port with `python manage.py runserver 8001`
2. **Database errors**: Run `python manage.py migrate` again
3. **API errors**: Check your OpenRouter API key in `.env`
4. **Import errors**: Ensure virtual environment is activated

### Getting Help:
- Check the logs in the `logs/` directory
- Review CONTRIBUTING.md for development guidelines
- Contact the team lead for support

## Development Notes
- The app uses SQLite for local development
- AI interpretations require an OpenRouter API key
- All sensitive data is stored in environment variables
- Logs are automatically rotated to prevent disk space issues

---

**Ready to explore the stars! 🌟** 