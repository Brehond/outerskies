#!/usr/bin/env python3
"""
Comprehensive test suite for background task processing system.
Tests all endpoints, task status tracking, and error handling.
"""

import requests
import json
import time
import sys
import os
from datetime import datetime
import base64
import hmac
import hashlib
import random
import string

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test data
TEST_CHART_DATA = {
    "date": "1990-01-01",
    "time": "12:00",
    "latitude": 45.5,
    "longitude": -64.3,
    "timezone_str": "America/Halifax",
    "zodiac_type": "tropical",
    "house_system": "placidus",
    "model_name": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000
}

TEST_INTERPRETATION_DATA = {
    "chart_data": {
        "julian_day": 2447892.5,
        "positions": {
            "Sun": {"sign": "Capricorn", "degree": 10.5},
            "Moon": {"sign": "Aries", "degree": 15.2}
        },
        "ascendant": {"sign": "Libra", "degree": 5.8},
        "houses": [{"sign": "Libra", "degree": 5.8}],
        "house_signs": ["Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo"]
    },
    "model_name": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 1000,
    "interpretation_type": "comprehensive"
}

TEST_EPHEMERIS_DATA = {
    "date": "1990-01-01",
    "time": "12:00",
    "latitude": 45.5,
    "longitude": -64.3,
    "timezone_str": "America/Halifax",
    "zodiac_type": "tropical",
    "house_system": "placidus"
}

API_KEY = os.getenv('API_KEY', 'test-api-key-for-testing')
API_SECRET = os.getenv('API_SECRET', 'test-api-secret-for-testing')

SIGNATURE_HEADER = 'X-Signature'
TIMESTAMP_HEADER = 'X-Timestamp'
NONCE_HEADER = 'X-Nonce'
API_KEY_HEADER = 'X-Api-Key'

PUBLIC_PATHS = [
    '/api/v1/auth/register/',
    '/api/v1/auth/login/',
    '/api/v1/auth/refresh/',
    '/api/v1/auth/logout/',
]

def generate_signature(method, path, query_string, timestamp, nonce, body, api_secret):
    if body:
        body = base64.b64encode(body).decode('utf-8')
    else:
        body = ''
    signature_string = f'{method}\n{path}\n{query_string}\n{timestamp}\n{nonce}\n{body}'
    return hmac.new(api_secret.encode(), signature_string.encode(), hashlib.sha256).hexdigest()

def get_signed_headers(method, path, body=None, query_string=''):
    timestamp = str(int(time.time()))
    nonce = f'testnonce{timestamp}{random.randint(1000,9999)}'
    sig = generate_signature(method, path, query_string, timestamp, nonce, body, API_SECRET)
    return {
        API_KEY_HEADER: API_KEY,
        SIGNATURE_HEADER: sig,
        TIMESTAMP_HEADER: timestamp,
        NONCE_HEADER: nonce,
    }

class BackgroundTaskTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def test_result(self, test_name, success, details=""):
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        self.log(f"{status} - {test_name}: {details}")
        
    def _request(self, method, url, json=None, params=None):
        """Helper to send signed requests to the API."""
        path = url.replace(BASE_URL, '')
        query_string = ''
        if params:
            from urllib.parse import urlencode
            query_string = urlencode(params)
        body = None
        if json is not None:
            import json as _json
            body = _json.dumps(json).encode('utf-8')
        # Do not sign public endpoints
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return self.session.request(method, url, json=json, params=params)
        headers = get_signed_headers(method, path, body, query_string)
        # Merge with session headers (e.g., Authorization)
        all_headers = dict(self.session.headers)
        all_headers.update(headers)
        return self.session.request(method, url, json=json, params=params, headers=all_headers)
    
    def authenticate(self):
        """Test user authentication"""
        try:
            # First, try to create a test user or login
            login_data = {
                "username": "testuser",
                "password": "testpass123"
            }
            response = self._request('POST', f"{API_BASE}/auth/login/", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                # Updated: extract tokens from nested structure inside 'data'
                tokens = data.get('data', {}).get('tokens', {})
                if 'access' in tokens:
                    self.auth_token = tokens['access']
                    self.session.headers.update({'Authorization': f'Bearer {self.auth_token}'})
                    self.test_result("Authentication", True, "Login successful")
                    return True
                else:
                    self.test_result("Authentication", False, "No access token in response")
                    return False
            else:
                # Try to register a new user
                register_data = {
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "testpass123",
                    "password_confirm": "testpass123",
                    "first_name": "Test",
                    "last_name": "User"
                }
                
                response = self._request('POST', f"{API_BASE}/auth/register/", json=register_data)
                
                if response.status_code == 201:
                    data = response.json()
                    # Updated: extract tokens from nested structure inside 'data'
                    tokens = data.get('data', {}).get('tokens', {})
                    if 'access' in tokens:
                        self.auth_token = tokens['access']
                        self.session.headers.update({'Authorization': f'Bearer {self.auth_token}'})
                        self.test_result("Authentication", True, "Registration and login successful")
                        return True
                    else:
                        self.test_result("Authentication", False, "No access token after registration")
                        return False
                else:
                    self.test_result("Authentication", False, f"Registration failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            self.test_result("Authentication", False, f"Authentication error: {str(e)}")
            return False
    
    def test_chart_generation(self):
        """Test background chart generation"""
        try:
            response = self._request('POST', f"{API_BASE}/background-charts/generate_chart/", json=TEST_CHART_DATA)
            
            if response.status_code == 202:
                data = response.json()
                if 'task_id' in data and 'status' in data:
                    self.test_result("Chart Generation - Task Creation", True, f"Task ID: {data['task_id']}")
                    return data['task_id']
                else:
                    self.test_result("Chart Generation - Task Creation", False, "Missing task_id or status in response")
                    return None
            else:
                self.test_result("Chart Generation - Task Creation", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.test_result("Chart Generation - Task Creation", False, f"Error: {str(e)}")
            return None
    
    def test_interpretation_generation(self):
        """Test background interpretation generation"""
        try:
            response = self._request('POST', f"{API_BASE}/background-charts/generate_interpretation/", json=TEST_INTERPRETATION_DATA)
            
            if response.status_code == 202:
                data = response.json()
                if 'task_id' in data and 'status' in data:
                    self.test_result("Interpretation Generation - Task Creation", True, f"Task ID: {data['task_id']}")
                    return data['task_id']
                else:
                    self.test_result("Interpretation Generation - Task Creation", False, "Missing task_id or status in response")
                    return None
            else:
                self.test_result("Interpretation Generation - Task Creation", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.test_result("Interpretation Generation - Task Creation", False, f"Error: {str(e)}")
            return None
    
    def test_ephemeris_calculation(self):
        """Test background ephemeris calculation"""
        try:
            response = self._request('POST', f"{API_BASE}/background-charts/calculate_ephemeris/", json=TEST_EPHEMERIS_DATA)
            
            if response.status_code == 202:
                data = response.json()
                if 'task_id' in data and 'status' in data:
                    self.test_result("Ephemeris Calculation - Task Creation", True, f"Task ID: {data['task_id']}")
                    return data['task_id']
                else:
                    self.test_result("Ephemeris Calculation - Task Creation", False, "Missing task_id or status in response")
                    return None
            else:
                self.test_result("Ephemeris Calculation - Task Creation", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.test_result("Ephemeris Calculation - Task Creation", False, f"Error: {str(e)}")
            return None
    
    def test_task_status_monitoring(self, task_id):
        """Test task status monitoring"""
        try:
            # First, get the task status from the database
            response = self._request('GET', f"{API_BASE}/tasks/")
            
            if response.status_code == 200:
                tasks = response.json()
                task_found = None
                
                for task in tasks:
                    if task.get('task_id') == task_id:
                        task_found = task
                        break
                
                if task_found:
                    task_db_id = task_found['id']
                    
                    # Test status endpoint
                    status_response = self._request('GET', f"{API_BASE}/tasks/{task_db_id}/status/")
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        self.test_result("Task Status Monitoring", True, f"State: {status_data.get('state', 'unknown')}")
                        return status_data
                    else:
                        self.test_result("Task Status Monitoring", False, f"Status endpoint failed: {status_response.status_code}")
                        return None
                else:
                    self.test_result("Task Status Monitoring", False, f"Task {task_id} not found in database")
                    return None
            else:
                self.test_result("Task Status Monitoring", False, f"Failed to get tasks: {response.status_code}")
                return None
                
        except Exception as e:
            self.test_result("Task Status Monitoring", False, f"Error: {str(e)}")
            return None
    
    def test_task_cancellation(self, task_id):
        """Test task cancellation"""
        try:
            # Get the task from database
            response = self._request('GET', f"{API_BASE}/tasks/")
            
            if response.status_code == 200:
                tasks = response.json()
                task_found = None
                
                for task in tasks:
                    if task.get('task_id') == task_id:
                        task_found = task
                        break
                
                if task_found and not task_found.get('is_completed', True):
                    task_db_id = task_found['id']
                    
                    # Test cancellation
                    cancel_response = self._request('POST', f"{API_BASE}/tasks/{task_db_id}/cancel/")
                    
                    if cancel_response.status_code == 200:
                        self.test_result("Task Cancellation", True, "Task cancelled successfully")
                        return True
                    else:
                        self.test_result("Task Cancellation", False, f"Cancellation failed: {cancel_response.status_code}")
                        return False
                else:
                    self.test_result("Task Cancellation", False, "Task not found or already completed")
                    return False
            else:
                self.test_result("Task Cancellation", False, f"Failed to get tasks: {response.status_code}")
                return False
                
        except Exception as e:
            self.test_result("Task Cancellation", False, f"Error: {str(e)}")
            return False
    
    def test_task_listing(self):
        """Test task listing functionality"""
        try:
            response = self._request('GET', f"{API_BASE}/tasks/")
            
            if response.status_code == 200:
                tasks = response.json()
                self.test_result("Task Listing", True, f"Found {len(tasks)} tasks")
                return tasks
            else:
                self.test_result("Task Listing", False, f"HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.test_result("Task Listing", False, f"Error: {str(e)}")
            return None
    
    def test_error_handling(self):
        """Test error handling with invalid data"""
        try:
            # Test with missing required fields
            invalid_data = {"date": "1990-01-01"}  # Missing other required fields
            
            response = self._request('POST', f"{API_BASE}/background-charts/generate_chart/", json=invalid_data)
            
            if response.status_code == 400:
                self.test_result("Error Handling - Invalid Data", True, "Properly rejected invalid data")
                return True
            else:
                self.test_result("Error Handling - Invalid Data", False, f"Expected 400, got {response.status_code}")
                return False
                
        except Exception as e:
            self.test_result("Error Handling - Invalid Data", False, f"Error: {str(e)}")
            return False
    
    def test_concurrent_tasks(self):
        """Test creating multiple concurrent tasks"""
        try:
            task_ids = []
            
            # Create 3 chart generation tasks
            for i in range(3):
                test_data = TEST_CHART_DATA.copy()
                test_data["date"] = f"199{i}-01-01"  # Different dates
                
                response = self._request('POST', f"{API_BASE}/background-charts/generate_chart/", json=test_data)
                
                if response.status_code == 202:
                    data = response.json()
                    if 'task_id' in data:
                        task_ids.append(data['task_id'])
            
            if len(task_ids) == 3:
                self.test_result("Concurrent Tasks", True, f"Created {len(task_ids)} concurrent tasks")
                return task_ids
            else:
                self.test_result("Concurrent Tasks", False, f"Only created {len(task_ids)} tasks")
                return task_ids
                
        except Exception as e:
            self.test_result("Concurrent Tasks", False, f"Error: {str(e)}")
            return []
    
    def wait_for_task_completion(self, task_id, timeout=300):
        """Wait for a task to complete and monitor progress"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Get task status
                response = self._request('GET', f"{API_BASE}/tasks/")
                
                if response.status_code == 200:
                    tasks = response.json()
                    
                    for task in tasks:
                        if task.get('task_id') == task_id:
                            state = task.get('state', 'UNKNOWN')
                            progress = task.get('progress', 0)
                            
                            self.log(f"Task {task_id}: {state} ({progress}%)")
                            
                            if task.get('is_completed', False):
                                if state == 'SUCCESS':
                                    self.test_result("Task Completion", True, f"Task {task_id} completed successfully")
                                    return True
                                elif state == 'FAILURE':
                                    self.test_result("Task Completion", False, f"Task {task_id} failed")
                                    return False
                            
                            break
                    
                    time.sleep(5)  # Wait 5 seconds before checking again
                else:
                    self.log(f"Failed to get task status: {response.status_code}")
                    time.sleep(5)
                    
            except Exception as e:
                self.log(f"Error monitoring task: {str(e)}")
                time.sleep(5)
        
        self.test_result("Task Completion", False, f"Task {task_id} timed out after {timeout} seconds")
        return False
    
    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        self.log("Starting comprehensive background task testing...")
        
        # Test 1: Authentication
        if not self.authenticate():
            self.log("Authentication failed. Cannot proceed with tests.")
            return
        
        # Test 2: Task Listing (empty)
        self.test_task_listing()
        
        # Test 3: Error Handling
        self.test_error_handling()
        
        # Test 4: Chart Generation
        chart_task_id = self.test_chart_generation()
        
        # Test 5: Interpretation Generation
        interpretation_task_id = self.test_interpretation_generation()
        
        # Test 6: Ephemeris Calculation
        ephemeris_task_id = self.test_ephemeris_calculation()
        
        # Test 7: Concurrent Tasks
        concurrent_task_ids = self.test_concurrent_tasks()
        
        # Test 8: Task Status Monitoring
        if chart_task_id:
            self.test_task_status_monitoring(chart_task_id)
        
        # Test 9: Task Listing (with tasks)
        self.test_task_listing()
        
        # Test 10: Wait for task completion
        if chart_task_id:
            self.wait_for_task_completion(chart_task_id, timeout=60)
        
        # Test 11: Task Cancellation (if any tasks are still running)
        if concurrent_task_ids:
            self.test_task_cancellation(concurrent_task_ids[0])
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("BACKGROUND TASK TESTING SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\nDetailed Results:")
        print("-" * 60)
        
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} - {result['test']}")
            if result['details']:
                print(f"    Details: {result['details']}")
        
        # Save results to file
        with open('background_task_test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\nDetailed results saved to: background_task_test_results.json")

if __name__ == "__main__":
    tester = BackgroundTaskTester()
    tester.run_comprehensive_test() 