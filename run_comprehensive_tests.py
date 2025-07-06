#!/usr/bin/env python3
"""
Comprehensive Test Runner for Phase 1 Production Deployment

This script runs all test suites for the production deployment features:
- Docker configurations
- Health checks and monitoring
- Deployment scripts and CI/CD
- Security configurations
- Documentation
"""

import os
import sys
import time
import unittest
from pathlib import Path
import importlib.util

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def import_test_module(module_name):
    """Import a test module dynamically"""
    module_path = project_root / f"{module_name}.py"
    
    if not module_path.exists():
        print(f"⚠️  Test module {module_name} not found: {module_path}")
        return None
        
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"❌ Error importing {module_name}: {e}")
        return None

def run_test_suite(test_module, suite_name):
    """Run a specific test suite"""
    print(f"\n{'='*60}")
    print(f"🧪 Running {suite_name} Tests")
    print(f"{'='*60}")
    
    if test_module is None:
        print(f"❌ Skipping {suite_name} tests - module not available")
        return None
        
    # Find the test runner function
    runner_function = None
    for attr_name in dir(test_module):
        if 'test' in attr_name.lower() and 'run' in attr_name.lower():
            runner_function = getattr(test_module, attr_name)
            break
            
    if runner_function is None:
        print(f"❌ No test runner function found in {suite_name}")
        return None
        
    try:
        start_time = time.time()
        result = runner_function()
        end_time = time.time()
        
        print(f"\n⏱️  {suite_name} tests completed in {end_time - start_time:.2f} seconds")
        return result
        
    except Exception as e:
        print(f"❌ Error running {suite_name} tests: {e}")
        return None

def run_all_tests():
    """Run all comprehensive tests"""
    print("🚀 COMPREHENSIVE PHASE 1 PRODUCTION DEPLOYMENT TEST SUITE")
    print("=" * 80)
    print("Testing all production deployment features...")
    print("=" * 80)
    
    # Define test suites to run
    test_suites = [
        ("tests_production_deployment", "Production Deployment"),
        ("tests_docker_integration", "Docker Integration"),
        ("tests_health_monitoring", "Health Monitoring"),
        ("tests_deployment_ci", "Deployment & CI/CD")
    ]
    
    # Track overall results
    total_tests = 0
    total_failures = 0
    total_errors = 0
    failed_suites = []
    
    start_time = time.time()
    
    # Run each test suite
    for module_name, suite_name in test_suites:
        test_module = import_test_module(module_name)
        result = run_test_suite(test_module, suite_name)
        
        if result is not None:
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            
            if result.failures or result.errors:
                failed_suites.append(suite_name)
        else:
            failed_suites.append(suite_name)
    
    end_time = time.time()
    
    # Print comprehensive summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    print(f"⏱️  Total execution time: {end_time - start_time:.2f} seconds")
    print(f"🧪 Total test suites run: {len(test_suites)}")
    print(f"📈 Total tests executed: {total_tests}")
    print(f"❌ Total failures: {total_failures}")
    print(f"💥 Total errors: {total_errors}")
    
    if total_tests > 0:
        success_rate = ((total_tests - total_failures - total_errors) / total_tests) * 100
        print(f"✅ Overall success rate: {success_rate:.1f}%")
    else:
        print("⚠️  No tests were executed")
    
    if failed_suites:
        print(f"\n❌ Failed test suites:")
        for suite in failed_suites:
            print(f"  - {suite}")
    else:
        print(f"\n✅ All test suites passed!")
    
    # Print detailed results
    print(f"\n{'='*80}")
    print("📋 DETAILED RESULTS")
    print(f"{'='*80}")
    
    for module_name, suite_name in test_suites:
        test_module = import_test_module(module_name)
        if test_module is not None:
            print(f"\n📦 {suite_name}:")
            
            # Count test classes
            test_classes = [cls for cls in dir(test_module) 
                          if cls.startswith('Test') and 
                          isinstance(getattr(test_module, cls), type)]
            
            print(f"  - Test classes: {len(test_classes)}")
            for cls in test_classes:
                print(f"    • {cls}")
    
    # Print recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if total_failures == 0 and total_errors == 0:
        print("✅ All tests passed! Your production deployment is ready.")
        print("🎉 You can proceed with confidence to deploy to production.")
    else:
        print("⚠️  Some tests failed. Please address the following:")
        print("   1. Review failed tests and fix issues")
        print("   2. Re-run tests to ensure fixes work")
        print("   3. Only deploy when all tests pass")
        
        if total_failures > 0:
            print(f"   4. Focus on {total_failures} test failures first")
        if total_errors > 0:
            print(f"   5. Address {total_errors} test errors")
    
    # Print next steps
    print(f"\n{'='*80}")
    print("🚀 NEXT STEPS")
    print(f"{'='*80}")
    
    if total_failures == 0 and total_errors == 0:
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
    
    return {
        'total_tests': total_tests,
        'total_failures': total_failures,
        'total_errors': total_errors,
        'failed_suites': failed_suites,
        'success_rate': ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
    }

def run_quick_tests():
    """Run a quick subset of critical tests"""
    print("⚡ QUICK CRITICAL TESTS")
    print("=" * 50)
    
    # Run only the most critical tests
    critical_suites = [
        ("tests_production_deployment", "Production Deployment")
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for module_name, suite_name in critical_suites:
        test_module = import_test_module(module_name)
        result = run_test_suite(test_module, suite_name)
        
        if result is not None:
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
    
    print(f"\n📊 Quick Test Summary:")
    print(f"Tests: {total_tests}, Failures: {total_failures}, Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("✅ Quick tests passed!")
    else:
        print("❌ Quick tests failed - run full test suite for details")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive production deployment tests')
    parser.add_argument('--quick', action='store_true', help='Run only critical tests')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.quick:
        run_quick_tests()
    else:
        results = run_all_tests()
        
        # Exit with appropriate code
        if results['total_failures'] > 0 or results['total_errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0) 