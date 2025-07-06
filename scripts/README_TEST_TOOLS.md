# Test Output Logging System

This directory contains tools for capturing and analyzing test output to help debug issues.

## Files

- `log_output.py` - Core logging system for capturing command and test output
- `run_tests.py` - Test runner that uses the logging system
- `README_TEST_TOOLS.md` - This file

## Quick Start

### Windows Users
```bash
# Run full test suite with logging
run_tests.bat full

# Run API tests only
run_tests.bat api

# Run tests excluding plugins
run_tests.bat no-plugins

# Run migrations first, then tests
run_tests.bat migrate
```

### All Users
```bash
# Run full test suite with logging
python scripts/run_tests.py full

# Run API tests only
python scripts/run_tests.py api

# Run tests excluding plugins
python scripts/run_tests.py no-plugins

# Run specific test
python scripts/run_tests.py api.tests.PaymentAPITests

# Run any command with logging
python scripts/log_output.py "python manage.py migrate"
```

## Output Files

All output is saved to the `logs/` directory:

- `logs/command_YYYYMMDD_HHMMSS.txt` - General command output
- `logs/tests/test_run_YYYYMMDD_HHMMSS.txt` - Detailed test output

## Features

### 1. Complete Output Capture
- Captures both stdout and stderr
- Records command, timestamp, and exit code
- Handles timeouts and exceptions

### 2. Test Analysis
- Automatically analyzes test results
- Extracts test counts (total, passed, failed, errors)
- Identifies specific error details
- Provides summary statistics

### 3. Multiple Test Modes
- Full test suite
- API tests only
- Tests excluding problematic plugins
- Specific test classes or methods

### 4. Error Debugging
- Detailed error logs with full stack traces
- Test failure analysis
- Command execution tracking

## Example Output

```
🧪 Running full Django test suite...

📊 Test Results:
   Success: ❌ No
   Exit Code: 1
   Test Log: logs/tests/test_run_20241201_143022.txt
   General Log: logs/command_20241201_143022.txt

🔍 Analyzing test failures...

📈 Test Analysis:
   Total Tests: 99
   Passed: 92
   Failed: 2
   Errors: 5
   Summary: Ran 99 tests in 45.234s

❌ Error Details (3 errors):
   Error 1:
   ======================================================================
   ERROR: test_list_user_charts (api.tests.ChartAPITests.test_list_user_charts)
   Test listing user charts
   ----------------------------------------------------------------------
   Traceback (most recent call last):
   ...
```

## Troubleshooting

### PowerShell Output Issues
If you're experiencing truncated output in PowerShell, use the logging system:
```bash
python scripts/run_tests.py full
```

### Database Issues
If tests fail due to missing database tables:
```bash
run_tests.bat migrate
```

### Plugin Test Issues
If plugin tests are failing due to missing database tables:
```bash
python scripts/run_tests.py no-plugins
```

### Specific Test Debugging
To debug a specific failing test:
```bash
python scripts/run_tests.py api.tests.PaymentAPITests.test_list_payments
```

## Log File Format

Each log file contains:
```
Command: python manage.py test --verbosity=1
Timestamp: 2024-12-01T14:30:22.123456
Exit Code: 1
================================================================================
STDOUT:
[OK] Plugin 'astrology_chat' registered successfully
[OK] Plugin 'example_plugin' registered successfully
Found 99 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...

STDERR:
Error response: {"status_code": 400, "path": "/api/v1/users/change_password/", ...}
...
```

## Integration with Development Workflow

1. **Before committing code**: Run `run_tests.bat full`
2. **When debugging API issues**: Run `run_tests.bat api`
3. **When plugin tests fail**: Run `run_tests.bat no-plugins`
4. **Check logs**: Review files in `logs/` directory for detailed error information

This system ensures that no test output is lost and provides comprehensive debugging information for any issues that arise. 