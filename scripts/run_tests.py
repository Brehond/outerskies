#!/usr/bin/env python
"""
Test runner script that uses the logging system to capture all test output.
This script provides a convenient way to run tests and analyze results.
"""

import sys
import os
from pathlib import Path

# Add the scripts directory to the path so we can import log_output
sys.path.insert(0, str(Path(__file__).parent))

from log_output import TestOutputLogger

def run_full_test_suite():
    """Run the full Django test suite with logging"""
    logger = TestOutputLogger()
    
    print("🧪 Running full Django test suite...")
    result = logger.run_django_test(verbosity=1)
    
    print(f"\n📊 Test Results:")
    print(f"   Success: {'✅ Yes' if result['success'] else '❌ No'}")
    print(f"   Exit Code: {result['exit_code']}")
    print(f"   Test Log: {result['test_log_file']}")
    print(f"   General Log: {result['general_log_file']}")
    
    if result['success']:
        print("\n🎉 All tests passed!")
    else:
        print("\n🔍 Analyzing test failures...")
        analysis = logger.analyze_test_output(result['test_log_file'])
        
        print(f"\n📈 Test Analysis:")
        print(f"   Total Tests: {analysis.get('total_tests', 'Unknown')}")
        print(f"   Passed: {analysis.get('passed_tests', 'Unknown')}")
        print(f"   Failed: {analysis.get('failed_tests', 'Unknown')}")
        print(f"   Errors: {analysis.get('errors', 'Unknown')}")
        print(f"   Summary: {analysis.get('test_summary', 'No summary found')}")
        
        if analysis.get('error_details'):
            print(f"\n❌ Error Details ({len(analysis['error_details'])} errors):")
            for i, error in enumerate(analysis['error_details'][:3], 1):  # Show first 3 errors
                print(f"   Error {i}:")
                print(f"   {error[:200]}...")
                if i < 3:
                    print()
    
    return result

def run_specific_test(test_path: str):
    """Run a specific test with logging"""
    logger = TestOutputLogger()
    
    print(f"🧪 Running specific test: {test_path}")
    result = logger.run_django_test(test_path=test_path, verbosity=2)
    
    print(f"\n📊 Test Results:")
    print(f"   Success: {'✅ Yes' if result['success'] else '❌ No'}")
    print(f"   Exit Code: {result['exit_code']}")
    print(f"   Test Log: {result['test_log_file']}")
    
    if not result['success']:
        print(f"\n📄 Full output available in: {result['test_log_file']}")
    
    return result

def run_api_tests():
    """Run API tests specifically"""
    logger = TestOutputLogger()
    
    print("🧪 Running API tests...")
    result = logger.run_django_test(test_path="api", verbosity=2)
    
    print(f"\n📊 API Test Results:")
    print(f"   Success: {'✅ Yes' if result['success'] else '❌ No'}")
    print(f"   Exit Code: {result['exit_code']}")
    print(f"   Test Log: {result['test_log_file']}")
    
    return result

def run_tests_excluding_plugins():
    """Run tests excluding plugin tests that have database issues"""
    logger = TestOutputLogger()
    
    print("🧪 Running tests (excluding plugins)...")
    result = logger.run_django_test(exclude="plugins.astrology_chat", verbosity=1)
    
    print(f"\n📊 Test Results (excluding plugins):")
    print(f"   Success: {'✅ Yes' if result['success'] else '❌ No'}")
    print(f"   Exit Code: {result['exit_code']}")
    print(f"   Test Log: {result['test_log_file']}")
    
    return result

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py <command>")
        print("\nAvailable commands:")
        print("  full          - Run full test suite")
        print("  api           - Run API tests only")
        print("  no-plugins    - Run tests excluding plugins")
        print("  <test_path>   - Run specific test (e.g., api.tests.PaymentAPITests)")
        return
    
    command = sys.argv[1].lower()
    
    if command == "full":
        run_full_test_suite()
    elif command == "api":
        run_api_tests()
    elif command == "no-plugins":
        run_tests_excluding_plugins()
    else:
        # Treat as specific test path
        run_specific_test(command)

if __name__ == "__main__":
    main() 