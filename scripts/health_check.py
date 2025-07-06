#!/usr/bin/env python3
"""
Health Check Script for Outer Skies

This script provides comprehensive health monitoring for the Outer Skies application.
It can be used by load balancers, monitoring systems, or manual health checks.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')

import django
django.setup()

from monitoring.health_checks import get_system_health, get_quick_health_status


def main():
    """Main health check function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Outer Skies Health Check')
    parser.add_argument('--quick', action='store_true', 
                       help='Perform quick health check only')
    parser.add_argument('--detailed', action='store_true',
                       help='Perform detailed health check')
    parser.add_argument('--json', action='store_true',
                       help='Output in JSON format')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if unhealthy')
    
    args = parser.parse_args()
    
    try:
        if args.quick:
            # Quick health check
            status = get_quick_health_status()
            if args.json:
                result = {
                    'status': status,
                    'timestamp': time.time(),
                    'check_type': 'quick'
                }
                print(json.dumps(result))
            else:
                print(f"Health Status: {status}")
            
            if args.exit_code and status != 'healthy':
                sys.exit(1)
            elif args.exit_code:
                sys.exit(0)
        else:
            # Detailed health check
            health_data = get_system_health()
            
            if args.json:
                print(json.dumps(health_data, indent=2))
            else:
                print_health_summary(health_data)
            
            if args.exit_code:
                if health_data['overall_status'] == 'unhealthy':
                    sys.exit(2)
                elif health_data['overall_status'] == 'degraded':
                    sys.exit(1)
                else:
                    sys.exit(0)
    
    except Exception as e:
        error_result = {
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }
        
        if args.json:
            print(json.dumps(error_result))
        else:
            print(f"Health check failed: {e}")
        
        if args.exit_code:
            sys.exit(3)


def print_health_summary(health_data):
    """Print a human-readable health summary"""
    print("=" * 60)
    print("OUTER SKIES HEALTH CHECK")
    print("=" * 60)
    print(f"Overall Status: {health_data['overall_status'].upper()}")
    print(f"Timestamp: {health_data['timestamp']}")
    print(f"Total Checks: {health_data['total_checks']}")
    print(f"Healthy: {health_data['healthy_count']}")
    print(f"Degraded: {health_data['degraded_count']}")
    print(f"Unhealthy: {health_data['unhealthy_count']}")
    print(f"Total Time: {health_data['total_time']}s")
    print()
    
    print("DETAILED RESULTS:")
    print("-" * 60)
    
    for check in health_data['checks']:
        status_icon = {
            'healthy': '✅',
            'degraded': '⚠️',
            'unhealthy': '❌'
        }.get(check['status'], '❓')
        
        print(f"{status_icon} {check['name'].upper()}: {check['status']}")
        print(f"   Response Time: {check['response_time']}s")
        
        if check['details']:
            print(f"   Details: {check['details']}")
        
        if check['error']:
            print(f"   Error: {check['error']}")
        
        print()


if __name__ == '__main__':
    main() 