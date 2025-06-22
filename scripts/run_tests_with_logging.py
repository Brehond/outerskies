#!/usr/bin/env python
"""
Comprehensive Test Runner with Logging
Captures and logs all test output, failures, and errors for better debugging.
"""

import os
import sys
import subprocess
import json
import datetime
from pathlib import Path
from typing import Dict, List, Any

class TestLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create timestamp for this test run
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"test_run_{self.timestamp}.log"
        self.json_file = self.log_dir / f"test_results_{self.timestamp}.json"
        
        # Test results storage
        self.test_results = {
            "timestamp": self.timestamp,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "test_details": [],
            "summary": {}
        }
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        
        # Write to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        
        # Also print to console
        print(log_entry)
    
    def run_test_command(self, command: List[str], test_name: str = "Unknown") -> Dict[str, Any]:
        """Run a test command and capture all output"""
        self.log(f"Running test: {test_name}")
        self.log(f"Command: {' '.join(command)}")
        
        result = {
            "test_name": test_name,
            "command": command,
            "start_time": datetime.datetime.now().isoformat(),
            "success": False,
            "output": "",
            "error": "",
            "return_code": -1,
            "duration": 0
        }
        
        try:
            start_time = datetime.datetime.now()
            
            # Run the command and capture output
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300  # 5 minute timeout
            )
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result.update({
                "return_code": process.returncode,
                "output": process.stdout,
                "error": process.stderr,
                "duration": duration,
                "success": process.returncode == 0
            })
            
            # Parse Django test output
            test_stats = self.parse_django_test_output(process.stdout)
            result.update(test_stats)
            
            if result["success"]:
                self.log(f"✓ {test_name} PASSED ({duration:.2f}s)")
            else:
                self.log(f"✗ {test_name} FAILED ({duration:.2f}s)")
                if process.stderr:
                    self.log(f"Error output: {process.stderr}", "ERROR")
            
        except subprocess.TimeoutExpired:
            result.update({
                "error": "Test timed out after 5 minutes",
                "success": False
            })
            self.log(f"✗ {test_name} TIMEOUT", "ERROR")
        except Exception as e:
            result.update({
                "error": str(e),
                "success": False
            })
            self.log(f"✗ {test_name} EXCEPTION: {e}", "ERROR")
        
        return result
    
    def parse_django_test_output(self, output: str) -> Dict[str, Any]:
        """Parse Django test output to extract statistics"""
        stats = {
            "tests_run": 0,
            "failures": 0,
            "errors": 0,
            "skipped": 0,
            "test_details": []
        }
        
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            
            # Look for test summary
            if "Ran" in line and "test" in line:
                try:
                    # Extract "Ran X test(s)" pattern
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "Ran":
                            stats["tests_run"] = int(parts[i + 1])
                        elif part == "FAILED":
                            stats["failures"] = int(parts[i - 1])
                        elif part == "ERROR":
                            stats["errors"] = int(parts[i - 1])
                        elif part == "skipped":
                            stats["skipped"] = int(parts[i - 1])
                except (ValueError, IndexError):
                    pass
            
            # Look for individual test results
            if line.startswith("FAIL:") or line.startswith("ERROR:"):
                test_detail = {
                    "type": "FAIL" if line.startswith("FAIL:") else "ERROR",
                    "test_name": line.split(":")[1].strip() if ":" in line else line,
                    "details": ""
                }
                stats["test_details"].append(test_detail)
        
        return stats
    
    def run_all_tests(self):
        """Run all test suites and generate comprehensive report"""
        self.log("Starting comprehensive test run")
        
        # Define test suites
        test_suites = [
            {
                "name": "Authentication Tests",
                "command": ["python", "manage.py", "test", "chart.tests.test_auth", "--verbosity=2"]
            },
            {
                "name": "Chart Model Tests", 
                "command": ["python", "manage.py", "test", "chart.tests.test_models", "--verbosity=2"]
            },
            {
                "name": "URL Tests",
                "command": ["python", "manage.py", "test", "chart.tests.test_urls", "--verbosity=2"]
            },
            {
                "name": "Security Tests",
                "command": ["python", "manage.py", "test", "chart.tests.test_security", "--verbosity=2"]
            },
            {
                "name": "All Chart Tests",
                "command": ["python", "manage.py", "test", "chart.tests", "--verbosity=2"]
            }
        ]
        
        # Run each test suite
        for suite in test_suites:
            result = self.run_test_command(suite["command"], suite["name"])
            self.test_results["test_details"].append(result)
            
            # Update summary statistics
            self.test_results["total_tests"] += result.get("tests_run", 0)
            self.test_results["passed"] += result.get("tests_run", 0) - result.get("failures", 0) - result.get("errors", 0)
            self.test_results["failed"] += result.get("failures", 0)
            self.test_results["errors"] += result.get("errors", 0)
            self.test_results["skipped"] += result.get("skipped", 0)
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        return self.test_results
    
    def generate_summary(self):
        """Generate a summary of all test results"""
        total = self.test_results["total_tests"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        errors = self.test_results["errors"]
        skipped = self.test_results["skipped"]
        
        if total > 0:
            success_rate = (passed / total) * 100
        else:
            success_rate = 0
        
        self.test_results["summary"] = {
            "success_rate": success_rate,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped
        }
        
        # Log summary
        self.log("=" * 60)
        self.log("TEST RUN SUMMARY")
        self.log("=" * 60)
        self.log(f"Total Tests: {total}")
        self.log(f"Passed: {passed}")
        self.log(f"Failed: {failed}")
        self.log(f"Errors: {errors}")
        self.log(f"Skipped: {skipped}")
        self.log(f"Success Rate: {success_rate:.1f}%")
        self.log("=" * 60)
    
    def save_results(self):
        """Save test results to JSON file"""
        with open(self.json_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        self.log(f"Test results saved to: {self.json_file}")
        self.log(f"Detailed log saved to: {self.log_file}")
    
    def generate_html_report(self):
        """Generate an HTML report from the test results"""
        html_file = self.log_dir / f"test_report_{self.timestamp}.html"
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {self.timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .error {{ color: #ffc107; }}
        .skipped {{ color: #6c757d; }}
        .test-detail {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .test-output {{ background: #000; color: #fff; padding: 10px; border-radius: 3px; font-family: monospace; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Test Report</h1>
        <p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <div class="summary-card">
            <h3>Total Tests</h3>
            <p class="passed">{self.test_results['summary']['total_tests']}</p>
        </div>
        <div class="summary-card">
            <h3>Passed</h3>
            <p class="passed">{self.test_results['summary']['passed']}</p>
        </div>
        <div class="summary-card">
            <h3>Failed</h3>
            <p class="failed">{self.test_results['summary']['failed']}</p>
        </div>
        <div class="summary-card">
            <h3>Errors</h3>
            <p class="error">{self.test_results['summary']['errors']}</p>
        </div>
        <div class="summary-card">
            <h3>Success Rate</h3>
            <p class="passed">{self.test_results['summary']['success_rate']:.1f}%</p>
        </div>
    </div>
    
    <h2>Test Details</h2>
"""
        
        for test_detail in self.test_results["test_details"]:
            status_class = "passed" if test_detail["success"] else "failed"
            status_icon = "✓" if test_detail["success"] else "✗"
            
            html_content += f"""
    <div class="test-detail">
        <h3>{status_icon} {test_detail['test_name']}</h3>
        <p><strong>Status:</strong> <span class="{status_class}">{'PASSED' if test_detail['success'] else 'FAILED'}</span></p>
        <p><strong>Duration:</strong> {test_detail['duration']:.2f}s</p>
        <p><strong>Tests Run:</strong> {test_detail.get('tests_run', 0)}</p>
        <p><strong>Failures:</strong> {test_detail.get('failures', 0)}</p>
        <p><strong>Errors:</strong> {test_detail.get('errors', 0)}</p>
"""
            
            if test_detail.get('output'):
                html_content += f"""
        <h4>Output:</h4>
        <div class="test-output">{test_detail['output']}</div>
"""
            
            if test_detail.get('error'):
                html_content += f"""
        <h4>Error:</h4>
        <div class="test-output">{test_detail['error']}</div>
"""
            
            html_content += """
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.log(f"HTML report generated: {html_file}")
        return html_file

def main():
    """Main function to run the test logger"""
    logger = TestLogger()
    
    try:
        # Run all tests
        results = logger.run_all_tests()
        
        # Generate HTML report
        html_file = logger.generate_html_report()
        
        # Print final summary
        print("\n" + "=" * 60)
        print("TEST RUN COMPLETED")
        print("=" * 60)
        print(f"Log file: {logger.log_file}")
        print(f"JSON results: {logger.json_file}")
        print(f"HTML report: {html_file}")
        print("=" * 60)
        
        # Return appropriate exit code
        if results["summary"]["failed"] > 0 or results["summary"]["errors"] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.log("Test run interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        logger.log(f"Unexpected error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 