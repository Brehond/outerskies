#!/usr/bin/env python3
"""
Comprehensive Celery test script that captures all output to a text file.
Tests both Celery and fallback scenarios with detailed logging.
"""

import os
import sys
import django
import logging
import time
import traceback
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astrology_ai.settings')
django.setup()

from django.conf import settings
from chart.celery_utils import create_task_with_fallback, is_celery_available
from chart.tasks import calculate_ephemeris_task, generate_chart_task, generate_interpretation_task

# Setup logging to capture everything
log_filename = f"celery_test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def test_celery_availability():
    """Test if Celery is available."""
    print("=== TESTING CELERY AVAILABILITY ===")
    logger.info("=== TESTING CELERY AVAILABILITY ===")
    
    try:
        available = is_celery_available()
        print(f"Celery available: {available}")
        logger.info(f"Celery available: {available}")
        return available
    except Exception as e:
        print(f"Error checking Celery availability: {e}")
        logger.error(f"Error checking Celery availability: {e}")
        logger.error(traceback.format_exc())
        return False

def test_simple_task():
    """Test a simple task execution."""
    print("\n=== TESTING SIMPLE TASK ===")
    logger.info("=== TESTING SIMPLE TASK ===")
    
    test_params = {
        'utc_date': '1990-01-01',
        'utc_time': '16:00',
        'latitude': 45.5,
        'longitude': -64.3,
        'zodiac_type': 'tropical',
        'house_system': 'placidus'
    }
    
    print(f"Test parameters: {test_params}")
    logger.info(f"Test parameters: {test_params}")
    
    try:
        print("Calling create_task_with_fallback...")
        logger.info("Calling create_task_with_fallback...")
        
        result = create_task_with_fallback(
            task_func=calculate_ephemeris_task,
            args=[test_params],
            user=None,
            task_type='ephemeris_test',
            parameters=test_params
        )
        
        print(f"Task result: {result}")
        logger.info(f"Task result: {result}")
        
        if result and result.get('success'):
            print("✅ Task executed successfully")
            logger.info("✅ Task executed successfully")
            return True
        else:
            print(f"❌ Task failed: {result}")
            logger.error(f"❌ Task failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Exception in task execution: {e}")
        logger.error(f"❌ Exception in task execution: {e}")
        logger.error(traceback.format_exc())
        return False

def test_chart_generation():
    """Test chart generation task."""
    print("\n=== TESTING CHART GENERATION ===")
    logger.info("=== TESTING CHART GENERATION ===")
    
    test_params = {
        'utc_date': '1990-01-01',
        'utc_time': '16:00',
        'latitude': 45.5,
        'longitude': -64.3,
        'zodiac_type': 'tropical',
        'house_system': 'placidus',
        'model_name': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 1000,
        'location': 'Test Location'
    }
    
    print(f"Chart generation parameters: {test_params}")
    logger.info(f"Chart generation parameters: {test_params}")
    
    try:
        result = create_task_with_fallback(
            task_func=generate_chart_task,
            args=[test_params],
            user=None,
            task_type='chart_generation_test',
            parameters=test_params
        )
        
        print(f"Chart generation result: {result}")
        logger.info(f"Chart generation result: {result}")
        
        if result and result.get('success'):
            print("✅ Chart generation executed successfully")
            logger.info("✅ Chart generation executed successfully")
            return True
        else:
            print(f"❌ Chart generation failed: {result}")
            logger.error(f"❌ Chart generation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Exception in chart generation: {e}")
        logger.error(f"❌ Exception in chart generation: {e}")
        logger.error(traceback.format_exc())
        return False

def test_interpretation_generation():
    """Test interpretation generation task."""
    print("\n=== TESTING INTERPRETATION GENERATION ===")
    logger.info("=== TESTING INTERPRETATION GENERATION ===")
    
    # Mock chart data
    chart_data = {
        'julian_day': 2447893.1666666665,
        'positions': {
            'Sun': {'sign': 'Capricorn', 'degree': 10.5},
            'Moon': {'sign': 'Aries', 'degree': 15.2}
        },
        'ascendant': {'sign': 'Aries', 'degree': 13.1},
        'houses': [0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330],
        'house_signs': ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 
                       'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    }
    
    interpretation_params = {
        'model_name': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 1000,
        'interpretation_type': 'comprehensive'
    }
    
    print(f"Interpretation parameters: {interpretation_params}")
    logger.info(f"Interpretation parameters: {interpretation_params}")
    
    try:
        result = create_task_with_fallback(
            task_func=generate_interpretation_task,
            args=[chart_data, interpretation_params],
            user=None,
            task_type='interpretation_test',
            parameters=interpretation_params
        )
        
        print(f"Interpretation result: {result}")
        logger.info(f"Interpretation result: {result}")
        
        if result and result.get('success'):
            print("✅ Interpretation generation executed successfully")
            logger.info("✅ Interpretation generation executed successfully")
            return True
        else:
            print(f"❌ Interpretation generation failed: {result}")
            logger.error(f"❌ Interpretation generation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Exception in interpretation generation: {e}")
        logger.error(f"❌ Exception in interpretation generation: {e}")
        logger.error(traceback.format_exc())
        return False

def test_direct_task_execution():
    """Test direct task execution without create_task_with_fallback."""
    print("\n=== TESTING DIRECT TASK EXECUTION ===")
    logger.info("=== TESTING DIRECT TASK EXECUTION ===")
    
    test_params = {
        'utc_date': '1990-01-01',
        'utc_time': '16:00',
        'latitude': 45.5,
        'longitude': -64.3,
        'zodiac_type': 'tropical',
        'house_system': 'placidus'
    }
    
    try:
        print("Testing direct task execution...")
        logger.info("Testing direct task execution...")
        
        # Test direct apply
        result = calculate_ephemeris_task.apply(args=[test_params])
        print(f"Direct task result: {result}")
        logger.info(f"Direct task result: {result}")
        print(f"Task successful: {result.successful()}")
        logger.info(f"Task successful: {result.successful()}")
        
        if result.successful():
            print(f"Task result: {result.result}")
            logger.info(f"Task result: {result.result}")
            return True
        else:
            print(f"Task failed: {result.result}")
            logger.error(f"Task failed: {result.result}")
            return False
            
    except Exception as e:
        print(f"❌ Exception in direct task execution: {e}")
        logger.error(f"❌ Exception in direct task execution: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Run all tests."""
    print("=== COMPREHENSIVE CELERY TESTING ===")
    logger.info("=== COMPREHENSIVE CELERY TESTING ===")
    print(f"Test output will be saved to: {log_filename}")
    logger.info(f"Test output will be saved to: {log_filename}")
    
    results = {}
    
    # Test 1: Celery availability
    results['celery_available'] = test_celery_availability()
    
    # Test 2: Simple task
    results['simple_task'] = test_simple_task()
    
    # Test 3: Chart generation
    results['chart_generation'] = test_chart_generation()
    
    # Test 4: Interpretation generation
    results['interpretation_generation'] = test_interpretation_generation()
    
    # Test 5: Direct task execution
    results['direct_execution'] = test_direct_task_execution()
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    logger.info("=== TEST SUMMARY ===")
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        logger.info(f"{status} - {test_name}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nOverall: {passed}/{total} tests passed")
    logger.info(f"Overall: {passed}/{total} tests passed")
    
    print(f"\nDetailed logs saved to: {log_filename}")
    logger.info(f"Detailed logs saved to: {log_filename}")
    
    return results

if __name__ == '__main__':
    main() 