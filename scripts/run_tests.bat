@echo off
REM Test Runner Batch Script for Windows
REM Captures test output and saves to logs directory

setlocal enabledelayedexpansion

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Get timestamp for filename
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

REM Set output file
set "output_file=logs\test_output_%timestamp%.txt"

echo Running Django tests with output capture...
echo Output will be saved to: %output_file%
echo.

REM Check if specific test was provided
if "%1"=="" (
    echo Running all authentication tests...
    python manage.py test chart.tests.test_auth --verbosity=2 > "%output_file%" 2>&1
    set "test_name=All Authentication Tests"
) else (
    echo Running specific test: %*
    python manage.py test %* --verbosity=2 > "%output_file%" 2>&1
    set "test_name=%*"
)

REM Check exit code
if %errorlevel% equ 0 (
    echo.
    echo ✓ Test completed successfully
    echo Results saved to: %output_file%
) else (
    echo.
    echo ✗ Test failed
    echo Error details saved to: %output_file%
)

REM Display the output
echo.
echo ========================================
echo TEST OUTPUT:
echo ========================================
type "%output_file%"

echo.
echo ========================================
echo END OF OUTPUT
echo ========================================
echo Results saved to: %output_file%

endlocal 