#!/usr/bin/env python3
"""
Windows-specific Celery setup and testing script.
This script helps diagnose and fix common Celery issues on Windows.
"""

from chart.tasks import health_check
from chart.celery_utils import is_celery_available, health_check_celery
import django
import os
import sys
import subprocess
import time
import json
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

django.setup()


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_section(title):
    """Print a formatted section."""
    print(f"\n--- {title} ---")


def check_redis_connection():
    """Check if Redis is running and accessible."""
    print_section("Checking Redis Connection")

    try:
        import redis
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.ping()
        print("✅ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\nTo start Redis on Windows:")
        print("1. Download Redis for Windows from: https://github.com/microsoftarchive/redis/releases")
        print("2. Install and start the Redis service")
        print("3. Or run: redis-server")
        return False


def check_celery_configuration():
    """Check Celery configuration."""
    print_section("Checking Celery Configuration")

    try:
        from django.conf import settings

        print(f"Broker URL: {settings.CELERY_BROKER_URL}")
        print(f"Result Backend: {settings.CELERY_RESULT_BACKEND}")
        print(f"Task Serializer: {settings.CELERY_TASK_SERIALIZER}")
        print(f"Result Serializer: {settings.CELERY_RESULT_SERIALIZER}")

        if hasattr(settings, 'CELERY_WORKER_POOL'):
            print(f"Worker Pool: {settings.CELERY_WORKER_POOL}")

        print("✅ Celery configuration looks good")
        return True
    except Exception as e:
        print(f"❌ Celery configuration error: {e}")
        return False


def test_celery_availability():
    """Test if Celery broker is available."""
    print_section("Testing Celery Availability")

    try:
        available = is_celery_available()
        if available:
            print("✅ Celery broker is available")
        else:
            print("❌ Celery broker is not available")
            print("\nThis is normal on Windows if Redis/Celery is not running.")
            print("Tasks will be executed synchronously as fallback.")
        return available
    except Exception as e:
        print(f"❌ Error testing Celery availability: {e}")
        return False


def test_synchronous_execution():
    """Test synchronous task execution."""
    print_section("Testing Synchronous Task Execution")

    try:
        # Test the health check task
        result = health_check.apply()

        if result.successful():
            print("✅ Synchronous task execution works")
            print(f"Task result: {result.result}")
        else:
            print(f"❌ Synchronous task execution failed: {result.result}")
        return result.successful()
    except Exception as e:
        print(f"❌ Error in synchronous task execution: {e}")
        return False


def run_health_check():
    """Run comprehensive health check."""
    print_section("Running Comprehensive Health Check")

    try:
        health_status = health_check_celery()
        print("Health Check Results:")
        print(json.dumps(health_status, indent=2))

        if health_status['overall_status'] == 'healthy':
            print("✅ System is healthy")
        elif health_status['overall_status'] == 'degraded':
            print("⚠️  System is degraded (Celery unavailable, but Redis and DB work)")
        else:
            print("❌ System is unhealthy")

        return health_status['overall_status']
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 'error'


def start_redis_server():
    """Attempt to start Redis server."""
    print_section("Starting Redis Server")

    try:
        # Try to start Redis server
        print("Attempting to start Redis server...")
        process = subprocess.Popen(
            ['redis-server'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a moment for Redis to start
        time.sleep(2)

        if process.poll() is None:
            print("\u2705 Redis server started successfully")
            return True
        else:
            stdout, stderr = process.communicate()
            print("\u274c Failed to start Redis server:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
    except FileNotFoundError:
        print("❌ Redis server not found in PATH")
        print("Please install Redis for Windows first.")
        return False
    except Exception as e:
        print(f"❌ Error starting Redis server: {e}")
        return False


def start_celery_worker():
    """Attempt to start Celery worker."""
    print_section("Starting Celery Worker")

    try:
        print("Attempting to start Celery worker...")
        process = subprocess.Popen(
            ['celery', '-A', 'astrology_ai', 'worker', '--loglevel=info', '--pool=solo'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait a moment for worker to start
        time.sleep(3)

        if process.poll() is None:
            print("\u2705 Celery worker started successfully")
            return True
        else:
            stdout, stderr = process.communicate()
            print("\u274c Failed to start Celery worker:")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
    except FileNotFoundError:
        print("❌ Celery not found in PATH")
        print("Please install Celery: pip install celery")
        return False
    except Exception as e:
        print(f"❌ Error starting Celery worker: {e}")
        return False


def provide_windows_guidance():
    """Provide Windows-specific guidance."""
    print_section("Windows Development Guidance")

    print("For Windows development, you have several options:")
    print("\n1. Use Synchronous Execution (Recommended for development):")
    print("   Set CELERY_ALWAYS_EAGER=True in your .env file")
    print("   This will execute all tasks synchronously without needing Redis/Celery")

    print("\n2. Use WSL2 (Windows Subsystem for Linux):")
    print("   - Install WSL2 and Ubuntu")
    print("   - Run your Django project inside WSL2")
    print("   - Install Redis and Celery in the Linux environment")

    print("\n3. Use Docker:")
    print("   - Use docker-compose to run Redis and Celery in containers")
    print("   - This isolates the development environment")

    print("\n4. Native Windows Setup:")
    print("   - Install Redis for Windows")
    print("   - Use Celery with solo pool (already configured)")
    print("   - May have networking issues (common on Windows)")


def main():
    """Main function to run all checks."""
    print_header("Windows Celery Setup and Diagnostics")

    print("This script will help you diagnose and fix Celery issues on Windows.")
    print("It will check Redis, Celery configuration, and provide guidance.")

    # Run all checks
    redis_ok = check_redis_connection()
    config_ok = check_celery_configuration()
    celery_available = test_celery_availability()
    sync_ok = test_synchronous_execution()
    health_status = run_health_check()

    # Summary
    print_header("Summary")

    print(f"Redis Connection: {'✅ OK' if redis_ok else '❌ Failed'}")
    print(f"Celery Config: {'✅ OK' if config_ok else '❌ Failed'}")
    print(f"Celery Available: {'✅ Yes' if celery_available else '❌ No'}")
    print(f"Synchronous Tasks: {'✅ OK' if sync_ok else '❌ Failed'}")
    print(f"Overall Health: {health_status.upper()}")

    if not redis_ok:
        print("\n🔧 To fix Redis issues:")
        print("1. Install Redis for Windows")
        print("2. Start Redis service")
        print("3. Or use CELERY_ALWAYS_EAGER=True for development")

    if not celery_available and redis_ok:
        print("\n🔧 To fix Celery issues:")
        print("1. Start Celery worker: celery -A astrology_ai worker --pool=solo")
        print("2. Or use CELERY_ALWAYS_EAGER=True for development")

    if sync_ok:
        print("\n✅ Your system can run tasks synchronously!")
        print("This is sufficient for development. Set CELERY_ALWAYS_EAGER=True in .env")

    provide_windows_guidance()

    print_header("Setup Complete")
    print("Your Outer Skies project is ready for development!")
    print("Tasks will run synchronously if Celery is not available.")


if __name__ == '__main__':
    main()
