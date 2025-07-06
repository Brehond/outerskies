#!/usr/bin/env python3
"""
Phase 1 Improvements Test Script

This script tests all Phase 1 improvements:
1. Redis Caching Layer
2. Enhanced Background Task System
3. Enhanced API Rate Limiting

Run with: python test_phase1_improvements.py
"""

import os
import sys
import django
import time
import json
import requests
from datetime import datetime, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings

# Import our new services
from chart.services.caching import cache_service, ephemeris_cache, ai_cache, user_cache
from chart.celery_utils import enhanced_celery_manager
from api.middleware.enhanced_rate_limit import UsageAnalytics
from chart.services.ephemeris import get_chart_data

User = get_user_model()


class Phase1ImprovementsTest:
    """
    Comprehensive test suite for Phase 1 improvements
    """
    
    def __init__(self):
        self.client = Client()
        self.test_user = None
        self.test_data = {
            'birth_date': '1990-05-15',
            'birth_time': '14:30',
            'latitude': 40.7128,
            'longitude': -74.0060,
            'timezone': 'America/New_York',
            'zodiac_type': 'tropical',
            'house_system': 'placidus'
        }
        self.results = {
            'caching_tests': {},
            'background_task_tests': {},
            'rate_limiting_tests': {},
            'overall_status': 'PENDING'
        }
    
    def run_all_tests(self):
        """Run all Phase 1 tests"""
        print("🚀 Starting Phase 1 Improvements Test Suite")
        print("=" * 60)
        
        try:
            # Test 1: Caching System
            print("\n📦 Testing Caching System...")
            self.test_caching_system()
            
            # Test 2: Background Task System
            print("\n⚡ Testing Background Task System...")
            self.test_background_task_system()
            
            # Test 3: Rate Limiting System
            print("\n🛡️ Testing Rate Limiting System...")
            self.test_rate_limiting_system()
            
            # Generate report
            self.generate_report()
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            self.results['overall_status'] = 'FAILED'
            self.generate_report()
    
    def test_caching_system(self):
        """Test the Redis caching layer"""
        print("  Testing ephemeris caching...")
        
        # Test 1: Ephemeris caching
        try:
            # First, calculate chart data to populate cache
            from chart.services.ephemeris import get_chart_data
            
            # First call - should calculate and cache
            start_time = time.time()
            result1 = get_chart_data(
                self.test_data['birth_date'],
                self.test_data['birth_time'],
                self.test_data['latitude'],
                self.test_data['longitude'],
                self.test_data['timezone'],
                self.test_data['zodiac_type'],
                self.test_data['house_system']
            )
            first_call_time = time.time() - start_time
            
            # Second call - should use cache
            start_time = time.time()
            result2 = get_chart_data(
                self.test_data['birth_date'],
                self.test_data['birth_time'],
                self.test_data['latitude'],
                self.test_data['longitude'],
                self.test_data['timezone'],
                self.test_data['zodiac_type'],
                self.test_data['house_system']
            )
            second_call_time = time.time() - start_time
            
            if result1 and result2 and second_call_time < first_call_time:
                self.results['caching_tests']['ephemeris_caching'] = 'PASSED'
                print(f"    ✅ Ephemeris caching: {first_call_time:.3f}s → {second_call_time:.3f}s")
            else:
                self.results['caching_tests']['ephemeris_caching'] = 'FAILED'
                print(f"    ❌ Ephemeris caching failed")
                
        except Exception as e:
            self.results['caching_tests']['ephemeris_caching'] = f'ERROR: {str(e)}'
            print(f"    ❌ Ephemeris caching error: {e}")
        
        # Test 2: Cache statistics
        print("  Testing cache statistics...")
        try:
            stats = cache_service.get_stats()
            if stats and 'hit_rate_percent' in stats:
                self.results['caching_tests']['cache_statistics'] = 'PASSED'
                print(f"    ✅ Cache statistics: {stats['hit_rate_percent']}% hit rate")
            else:
                self.results['caching_tests']['cache_statistics'] = 'FAILED'
                print(f"    ❌ Cache statistics failed")
        except Exception as e:
            self.results['caching_tests']['cache_statistics'] = f'ERROR: {str(e)}'
            print(f"    ❌ Cache statistics error: {e}")
        
        # Test 3: User session caching
        print("  Testing user session caching...")
        try:
            test_preferences = {
                'preferred_zodiac_type': 'tropical',
                'preferred_house_system': 'placidus',
                'preferred_ai_model': 'gpt-4'
            }
            
            # Set preferences
            user_cache.cache_user_preferences(1, test_preferences)
            
            # Get preferences
            cached_prefs = user_cache.get_user_preferences(1)
            
            if cached_prefs == test_preferences:
                self.results['caching_tests']['user_session_caching'] = 'PASSED'
                print(f"    ✅ User session caching: {len(test_preferences)} preferences cached")
            else:
                self.results['caching_tests']['user_session_caching'] = 'FAILED'
                print(f"    ❌ User session caching failed")
                
        except Exception as e:
            self.results['caching_tests']['user_session_caching'] = f'ERROR: {str(e)}'
            print(f"    ❌ User session caching error: {e}")
    
    def test_background_task_system(self):
        """Test the enhanced background task system"""
        print("  Testing Celery availability...")
        
        # Test 1: Celery availability
        try:
            is_available = enhanced_celery_manager.is_celery_available()
            self.results['background_task_tests']['celery_availability'] = 'PASSED' if is_available else 'DEGRADED'
            print(f"    {'✅' if is_available else '⚠️'} Celery available: {is_available}")
        except Exception as e:
            self.results['background_task_tests']['celery_availability'] = f'ERROR: {str(e)}'
            print(f"    ❌ Celery availability error: {e}")
        
        # Test 2: System health
        print("  Testing system health...")
        try:
            health = enhanced_celery_manager.get_system_health()
            if health and 'celery_available' in health:
                self.results['background_task_tests']['system_health'] = 'PASSED'
                print(f"    ✅ System health: {health['platform']} platform")
            else:
                self.results['background_task_tests']['system_health'] = 'FAILED'
                print(f"    ❌ System health failed")
        except Exception as e:
            self.results['background_task_tests']['system_health'] = f'ERROR: {str(e)}'
            print(f"    ❌ System health error: {e}")
        
        # Test 3: Task creation (simulated)
        print("  Testing task creation...")
        try:
            # Simulate task creation
            task_params = {
                'birth_data': self.test_data,
                'user_id': 1,
                'task_type': 'chart_generation'
            }
            
            # This would normally create a task, but we'll just test the interface
            task_status = enhanced_celery_manager._create_task_status_record(
                'chart_generation', task_params, 1, 5, 3
            )
            
            if task_status and task_status.task_id:
                self.results['background_task_tests']['task_creation'] = 'PASSED'
                print(f"    ✅ Task creation: {task_status.task_id}")
            else:
                self.results['background_task_tests']['task_creation'] = 'FAILED'
                print(f"    ❌ Task creation failed")
                
        except Exception as e:
            self.results['background_task_tests']['task_creation'] = f'ERROR: {str(e)}'
            print(f"    ❌ Task creation error: {e}")
    
    def test_rate_limiting_system(self):
        """Test the enhanced rate limiting system"""
        print("  Testing usage analytics...")
        
        # Test 1: Usage analytics
        try:
            daily_stats = UsageAnalytics.get_daily_usage_stats()
            if daily_stats and 'date' in daily_stats:
                self.results['rate_limiting_tests']['usage_analytics'] = 'PASSED'
                print(f"    ✅ Usage analytics: {daily_stats['date']}")
            else:
                self.results['rate_limiting_tests']['usage_analytics'] = 'FAILED'
                print(f"    ❌ Usage analytics failed")
        except Exception as e:
            self.results['rate_limiting_tests']['usage_analytics'] = f'ERROR: {str(e)}'
            print(f"    ❌ Usage analytics error: {e}")
        
        # Test 2: Cost estimation
        print("  Testing cost estimation...")
        try:
            cost = UsageAnalytics.estimate_ai_cost(100, 'gpt-4')
            if cost > 0:
                self.results['rate_limiting_tests']['cost_estimation'] = 'PASSED'
                print(f"    ✅ Cost estimation: ${cost:.2f} for 100 interpretations")
            else:
                self.results['rate_limiting_tests']['cost_estimation'] = 'FAILED'
                print(f"    ❌ Cost estimation failed")
        except Exception as e:
            self.results['rate_limiting_tests']['cost_estimation'] = f'ERROR: {str(e)}'
            print(f"    ❌ Cost estimation error: {e}")
        
        # Test 3: User usage summary
        print("  Testing user usage summary...")
        try:
            usage_summary = UsageAnalytics.get_user_usage_summary(1, 30)
            if usage_summary and 'user_id' in usage_summary:
                self.results['rate_limiting_tests']['user_usage_summary'] = 'PASSED'
                print(f"    ✅ User usage summary: {usage_summary['period_days']} days")
            else:
                self.results['rate_limiting_tests']['user_usage_summary'] = 'FAILED'
                print(f"    ❌ User usage summary failed")
        except Exception as e:
            self.results['rate_limiting_tests']['user_usage_summary'] = f'ERROR: {str(e)}'
            print(f"    ❌ User usage summary error: {e}")
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n" + "=" * 60)
        print("📊 PHASE 1 IMPROVEMENTS TEST REPORT")
        print("=" * 60)
        
        # Calculate overall status
        all_tests = []
        for category in self.results.values():
            if isinstance(category, dict):
                all_tests.extend(category.values())
        
        passed_tests = sum(1 for test in all_tests if test == 'PASSED')
        total_tests = len(all_tests)
        
        if passed_tests == total_tests:
            self.results['overall_status'] = 'PASSED'
        elif passed_tests > total_tests * 0.7:
            self.results['overall_status'] = 'DEGRADED'
        else:
            self.results['overall_status'] = 'FAILED'
        
        # Print results
        print(f"\nOverall Status: {self.results['overall_status']}")
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        
        print("\n📦 Caching System Tests:")
        for test_name, result in self.results['caching_tests'].items():
            status_icon = "✅" if result == 'PASSED' else "❌" if result == 'FAILED' else "⚠️"
            print(f"  {status_icon} {test_name}: {result}")
        
        print("\n⚡ Background Task System Tests:")
        for test_name, result in self.results['background_task_tests'].items():
            status_icon = "✅" if result == 'PASSED' else "❌" if result == 'FAILED' else "⚠️"
            print(f"  {status_icon} {test_name}: {result}")
        
        print("\n🛡️ Rate Limiting System Tests:")
        for test_name, result in self.results['rate_limiting_tests'].items():
            status_icon = "✅" if result == 'PASSED' else "❌" if result == 'FAILED' else "⚠️"
            print(f"  {status_icon} {test_name}: {result}")
        
        # Performance metrics
        print("\n📈 Performance Metrics:")
        cache_stats = cache_service.get_stats()
        if cache_stats:
            print(f"  Cache Hit Rate: {cache_stats.get('hit_rate_percent', 0)}%")
            print(f"  Total Cache Requests: {cache_stats.get('total_requests', 0)}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if self.results['overall_status'] == 'PASSED':
            print("  ✅ All Phase 1 improvements are working correctly!")
            print("  🚀 Ready to proceed with Phase 2 development.")
        elif self.results['overall_status'] == 'DEGRADED':
            print("  ⚠️ Most improvements are working, but some issues detected.")
            print("  🔧 Review failed tests and address issues before Phase 2.")
        else:
            print("  ❌ Multiple issues detected in Phase 1 improvements.")
            print("  🛠️ Fix critical issues before proceeding with development.")
        
        # Save detailed report
        report_file = f"phase1_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")


def main():
    """Main test runner"""
    print("Outer Skies - Phase 1 Improvements Test Suite")
    print("Testing: Caching, Background Tasks, Rate Limiting")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run tests
    test_suite = Phase1ImprovementsTest()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main() 