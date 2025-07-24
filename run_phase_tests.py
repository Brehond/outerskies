#!/usr/bin/env python3
"""
Simple Test Runner for All Three Phases

This script provides an easy way to run comprehensive tests for all phases:
- Phase 1: Critical Backend Fixes
- Phase 2: Advanced Features  
- Phase 3: Production Readiness
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(command, description):
    """Run a command and return the result"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Running: {command}")
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        end_time = time.time()
        
        print(f"\n⏱️  Completed in {end_time - start_time:.2f} seconds")
        print(f"Exit code: {result.returncode}")
        
        if result.stdout:
            print(f"\n📤 Output:")
            print(result.stdout)
        
        if result.stderr:
            print(f"\n⚠️  Errors:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False

def run_django_tests():
    """Run Django tests using manage.py"""
    return run_command(
        "python manage.py test --verbosity=2",
        "Running Django Tests"
    )

def run_pytest_tests():
    """Run pytest tests"""
    return run_command(
        "python -m pytest --verbose --tb=short",
        "Running Pytest Tests"
    )

def run_comprehensive_tests():
    """Run the comprehensive test suite"""
    return run_command(
        "python test_all_phases.py",
        "Running Comprehensive Phase Tests"
    )

def run_security_tests():
    """Run security-specific tests"""
    return run_command(
        "python -m pytest chart/tests/test_security_features.py -v",
        "Running Security Tests"
    )

def run_api_tests():
    """Run API-specific tests"""
    return run_command(
        "python -m pytest api/tests.py -v",
        "Running API Tests"
    )

def run_performance_tests():
    """Run performance tests"""
    return run_command(
        "python -m pytest -m performance -v",
        "Running Performance Tests"
    )

def check_dependencies():
    """Check if all required dependencies are installed"""
    print(f"\n{'='*60}")
    print("🔍 Checking Dependencies")
    print(f"{'='*60}")
    
    required_packages = [
        'django',
        'redis',
        'celery',
        'pytest',
        'pytest-django',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Please install missing packages with: pip install " + " ".join(missing_packages))
        return False
    
    print("\n✅ All dependencies are installed!")
    return True

def main():
    """Main test runner"""
    print("🚀 COMPREHENSIVE TEST SUITE FOR ALL THREE PHASES")
    print("=" * 80)
    print("Testing Phase 1: Critical Backend Fixes")
    print("Testing Phase 2: Advanced Features")
    print("Testing Phase 3: Production Readiness")
    print("=" * 80)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependencies check failed. Please install missing packages.")
        sys.exit(1)
    
    # Track results
    test_results = {}
    
    # Run different test suites
    test_suites = [
        ("Django Tests", run_django_tests),
        ("Pytest Tests", run_pytest_tests),
        ("Comprehensive Phase Tests", run_comprehensive_tests),
        ("Security Tests", run_security_tests),
        ("API Tests", run_api_tests),
        ("Performance Tests", run_performance_tests)
    ]
    
    for test_name, test_function in test_suites:
        test_results[test_name] = test_function()
    
    # Print summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    total_tests = len(test_suites)
    passed_tests = sum(test_results.values())
    failed_tests = total_tests - passed_tests
    
    print(f"🧪 Total test suites: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    
    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        print(f"📈 Success rate: {success_rate:.1f}%")
    
    print(f"\n📋 Detailed Results:")
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  - {test_name}: {status}")
    
    # Print recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if failed_tests == 0:
        print("🎉 All test suites passed! Your system is ready for production.")
        print("✅ You can proceed with confidence to deploy.")
    else:
        print("⚠️  Some test suites failed. Please address the following:")
        print("   1. Review failed test outputs above")
        print("   2. Fix any issues identified")
        print("   3. Re-run tests to ensure fixes work")
        print("   4. Only deploy when all tests pass")
    
    # Print next steps
    print(f"\n{'='*80}")
    print("🚀 NEXT STEPS")
    print(f"{'='*80}")
    
    if failed_tests == 0:
        print("1. 🐳 Build and test Docker containers")
        print("2. 🔧 Configure production environment variables")
        print("3. 🌐 Set up nginx and SSL certificates")
        print("4. 📊 Configure monitoring and alerting")
        print("5. 🔄 Set up CI/CD pipeline")
        print("6. 🚀 Deploy to production server")
        print("7. ✅ Run post-deployment health checks")
    else:
        print("1. 🔍 Review test failures and errors")
        print("2. 🛠️  Fix identified issues")
        print("3. 🧪 Re-run tests to verify fixes")
        print("4. 📝 Update documentation if needed")
        print("5. 🔄 Repeat until all tests pass")
    
    # Exit with appropriate code
    if failed_tests == 0:
        print("\n🎉 All tests passed! Exiting with success code.")
        sys.exit(0)
    else:
        print(f"\n❌ {failed_tests} test suites failed. Exiting with error code.")
        sys.exit(1)

if __name__ == '__main__':
    main() 