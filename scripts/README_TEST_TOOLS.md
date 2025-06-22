# Test Output Capture Tools

This directory contains tools for capturing and analyzing Django test output to help with debugging test failures.

## Tools Available

### 1. Comprehensive Test Runner (`run_tests_with_logging.py`)

A full-featured test runner that:
- Runs multiple test suites
- Captures all output (stdout/stderr)
- Generates JSON reports
- Creates HTML reports
- Provides detailed statistics

**Usage:**
```bash
python scripts/run_tests_with_logging.py
```

**Output:**
- `logs/test_run_YYYYMMDD_HHMMSS.log` - Detailed log file
- `logs/test_results_YYYYMMDD_HHMMSS.json` - JSON results
- `logs/test_report_YYYYMMDD_HHMMSS.html` - HTML report

### 2. Simple Test Output Capture (`capture_test_output.py`)

Captures output for a specific test command.

**Usage:**
```bash
python scripts/capture_test_output.py "python manage.py test chart.tests.test_auth.TestAuthFlow.test_registration_password_mismatch"
```

**Output:**
- `logs/test_output_YYYYMMDD_HHMMSS.txt` - Complete test output

### 3. Windows Batch Script (`run_tests.bat`)

Simple batch script for Windows users.

**Usage:**
```cmd
# Run all authentication tests
scripts\run_tests.bat

# Run specific test
scripts\run_tests.bat chart.tests.test_auth.TestAuthFlow.test_registration_password_mismatch
```

### 4. PowerShell Script (`run_tests.ps1`)

PowerShell script with better error handling and formatting.

**Usage:**
```powershell
# Run all authentication tests
.\scripts\run_tests.ps1

# Run specific test
.\scripts\run_tests.ps1 -TestPath "chart.tests.test_auth.TestAuthFlow.test_registration_password_mismatch"

# Run with different verbosity
.\scripts\run_tests.ps1 -TestPath "chart.tests.test_auth" -Verbosity "3"
```

## Quick Start for Debugging Test Failures

1. **Run the failing test with output capture:**
   ```powershell
   .\scripts\run_tests.ps1 -TestPath "chart.tests.test_auth.TestAuthFlow.test_registration_password_mismatch"
   ```

2. **Check the output file:**
   - Look for the generated file in `logs/test_output_YYYYMMDD_HHMMSS.txt`
   - This contains the complete test output including any error messages

3. **For comprehensive analysis:**
   ```bash
   python scripts/run_tests_with_logging.py
   ```
   - This will run all test suites and generate detailed reports

## Understanding Test Output

### Common Test Failure Patterns

1. **Template Not Found:**
   ```
   TemplateDoesNotExist: chart/auth/some_template.html
   ```
   - Solution: Create the missing template file

2. **URL Reverse Error:**
   ```
   NoReverseMatch: Reverse for 'some_url' not found
   ```
   - Solution: Check URL configuration and namespacing

3. **Database Errors:**
   ```
   django.db.utils.IntegrityError
   ```
   - Solution: Check model constraints and test data

4. **Email Backend Issues:**
   ```
   AssertionError: 0 != 1  # Expected email to be sent
   ```
   - Solution: Configure email backend for testing

### Reading the Log Files

- **Log files** contain timestamped entries with test progress
- **JSON files** contain structured data for programmatic analysis
- **HTML reports** provide a visual summary of test results
- **Text output files** contain the raw Django test output

## Best Practices

1. **Always capture output** when debugging test failures
2. **Use specific test paths** rather than running all tests
3. **Check the logs directory** for historical test runs
4. **Use the HTML reports** for team communication
5. **Keep test output files** for regression analysis

## Troubleshooting

### PowerShell Execution Policy
If you get execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Python Path Issues
Ensure you're in the project root directory when running scripts:
```bash
cd /path/to/outer-skies
python scripts/capture_test_output.py "python manage.py test ..."
```

### Permission Issues
Make sure the `logs` directory is writable:
```bash
mkdir -p logs
chmod 755 logs
```

## Integration with CI/CD

These tools can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Tests with Output Capture
  run: |
    python scripts/run_tests_with_logging.py
    # Upload test reports as artifacts
    - name: Upload Test Reports
      uses: actions/upload-artifact@v2
      with:
        name: test-reports
        path: logs/
``` 