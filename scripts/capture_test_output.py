#!/usr/bin/env python
"""
Test Output Capture Script
Captures and saves test output for debugging specific test failures.
"""

import os
import sys
import subprocess
import datetime
from pathlib import Path


def capture_test_output(test_command, output_file=None):
    """Capture test output and save to file"""
    if output_file is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"logs/test_output_{timestamp}.txt"

    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)

    print(f"Running: {' '.join(test_command)}")
    print(f"Output will be saved to: {output_file}")
    print("-" * 60)

    try:
        # Run the test command
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300
        )

        # Prepare output content
        output_content = f"""Test Command: {' '.join(test_command)}
Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Return Code: {result.returncode}

{'='*60}
STDOUT:
{'='*60}
{result.stdout}

{'='*60}
STDERR:
{'='*60}
{result.stderr}

{'='*60}
SUMMARY:
{'='*60}
Exit Code: {result.returncode}
Success: {'Yes' if result.returncode == 0 else 'No'}
"""

        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)

        # Also print to console
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        print(f"\nOutput saved to: {output_file}")
        return result.returncode == 0

    except subprocess.TimeoutExpired:
        error_msg = f"Test timed out after 5 minutes\nCommand: {' '.join(test_command)}"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        print(f"Test timed out. Error saved to: {output_file}")
        return False
    except Exception as e:
        error_msg = f"Exception running test: {e}\nCommand: {' '.join(test_command)}"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(error_msg)
        print(f"Exception occurred. Error saved to: {output_file}")
        return False


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/capture_test_output.py <test_command>")
        print("Example: python scripts/capture_test_output.py 'python manage.py test chart.tests.test_auth.TestAuthFlow.test_registration_password_mismatch'")
        sys.exit(1)

    # Parse command
    test_command = sys.argv[1].split()

    # Capture output
    success = capture_test_output(test_command)

    if success:
        print("\n✓ Test completed successfully")
        sys.exit(0)
    else:
        print("\n✗ Test failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
