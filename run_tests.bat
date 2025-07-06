@echo off
REM Test runner batch file for Windows
REM This file provides easy access to run tests with logging

echo.
echo ========================================
echo    Outer Skies Test Runner
echo ========================================
echo.

if "%1"=="" (
    echo Usage: run_tests.bat [command]
    echo.
    echo Available commands:
    echo   full          - Run full test suite
    echo   api           - Run API tests only
    echo   no-plugins    - Run tests excluding plugins
    echo   payment       - Run payment tests only
    echo   chart         - Run chart tests only
    echo   migrate       - Run migrations first, then tests
    echo.
    echo Examples:
    echo   run_tests.bat full
    echo   run_tests.bat api
    echo   run_tests.bat no-plugins
    echo.
    pause
    exit /b 1
)

echo Running tests with command: %1
echo.

if "%1"=="migrate" (
    echo Running migrations first...
    python manage.py migrate
    echo.
    echo Now running full test suite...
    python scripts/run_tests.py full
) else (
    python scripts/run_tests.py %1
)

echo.
echo Test run completed. Check the logs/ directory for detailed output.
echo.
pause 