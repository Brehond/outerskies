@echo off
echo ============================================================
echo    Outer Skies - Windows Celery Setup and Diagnostics
echo ============================================================
echo.

echo This script will help you set up Celery for Windows development.
echo.

REM Check if virtual environment exists
if not exist "venv311\Scripts\activate.bat" (
    echo ❌ Virtual environment not found!
    echo Please run: python -m venv venv311
    echo Then run: venv311\Scripts\activate
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call venv311\Scripts\activate.bat

REM Check if Django settings are available
if not exist "astrology_ai\settings.py" (
    echo ❌ Django settings not found!
    echo Please make sure you're in the correct directory.
    echo.
    pause
    exit /b 1
)

REM Run the Python setup script
echo Running Celery diagnostics...
python scripts\setup_celery_windows.py

echo.
echo ============================================================
echo Setup complete! Check the output above for any issues.
echo ============================================================
echo.

REM Provide next steps
echo Next steps:
echo 1. If you want to use synchronous execution (recommended for development):
echo    Add CELERY_ALWAYS_EAGER=True to your .env file
echo.
echo 2. If you want to use background tasks:
echo    - Install Redis for Windows
echo    - Start Redis server
echo    - Start Celery worker: celery -A astrology_ai worker --pool=solo
echo.
echo 3. Start Django development server:
echo    python manage.py runserver
echo.

pause 