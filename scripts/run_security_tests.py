import os
import sys
import django
from django.core.management import execute_from_command_line
from django.test.utils import get_runner
from django.conf import settings

def run_tests():
    """Run security tests."""
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chart.tests.test_settings')
    django.setup()
    
    # Get test runner
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=True)
    
    # Run tests
    failures = test_runner.run_tests(['chart.tests.test_security_features'])
    
    # Print results
    if failures:
        print("\nSecurity tests failed! Please fix the issues before deploying.")
        sys.exit(1)
    else:
        print("\nAll security tests passed!")
        
def main():
    """Main function."""
    print("Running security tests...")
    run_tests()
    
if __name__ == '__main__':
    main() 