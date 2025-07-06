#!/usr/bin/env python
"""
Output logging system for capturing terminal and test command output.
This script provides utilities to capture, log, and analyze command output.
"""

import os
import sys
import subprocess
import datetime
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

class OutputLogger:
    """System for logging command output to text files"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log_command(self, command: str, output: str, error: str = "", exit_code: int = 0) -> str:
        """Log a command execution with its output"""
        log_file = self.log_dir / f"command_{self.timestamp}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Command: {command}\n")
            f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
            f.write(f"Exit Code: {exit_code}\n")
            f.write("=" * 80 + "\n")
            
            if output:
                f.write("STDOUT:\n")
                f.write(output)
                f.write("\n")
            
            if error:
                f.write("STDERR:\n")
                f.write(error)
                f.write("\n")
        
        return str(log_file)
    
    def run_and_log(self, command: str, timeout: int = 300) -> Dict[str, Any]:
        """Run a command and log its output"""
        print(f"Running: {command}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8'
            )
            
            log_file = self.log_command(
                command,
                result.stdout,
                result.stderr,
                result.returncode
            )
            
            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'log_file': log_file
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            log_file = self.log_command(command, "", error_msg, -1)
            return {
                'success': False,
                'exit_code': -1,
                'stdout': "",
                'stderr': error_msg,
                'log_file': log_file
            }
        except Exception as e:
            error_msg = f"Command failed with exception: {str(e)}"
            log_file = self.log_command(command, "", error_msg, -1)
            return {
                'success': False,
                'exit_code': -1,
                'stdout': "",
                'stderr': error_msg,
                'log_file': log_file
            }

class TestOutputLogger(OutputLogger):
    """Specialized logger for Django test output"""
    
    def __init__(self, log_dir: str = "logs"):
        super().__init__(log_dir)
        self.test_log_dir = self.log_dir / "tests"
        self.test_log_dir.mkdir(exist_ok=True)
    
    def run_django_test(self, test_path: str = "", verbosity: int = 1, 
                       exclude: str = "", keepdb: bool = False) -> Dict[str, Any]:
        """Run Django tests and log the output"""
        command_parts = ["python", "manage.py", "test"]
        
        if test_path:
            command_parts.append(test_path)
        
        if verbosity:
            command_parts.extend(["--verbosity", str(verbosity)])
        
        if exclude:
            command_parts.extend(["--exclude", exclude])
        
        if keepdb:
            command_parts.append("--keepdb")
        
        command = " ".join(command_parts)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        test_log_file = self.test_log_dir / f"test_run_{timestamp}.txt"
        
        print(f"Running Django test: {command}")
        print(f"Test log will be saved to: {test_log_file}")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes for tests
                encoding='utf-8'
            )
            
            # Save detailed test output
            with open(test_log_file, 'w', encoding='utf-8') as f:
                f.write(f"Test Command: {command}\n")
                f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                f.write(f"Exit Code: {result.returncode}\n")
                f.write("=" * 80 + "\n")
                
                if result.stdout:
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                    f.write("\n")
                
                if result.stderr:
                    f.write("STDERR:\n")
                    f.write(result.stderr)
                    f.write("\n")
            
            # Also log to general command log
            general_log_file = self.log_command(
                command,
                result.stdout,
                result.stderr,
                result.returncode
            )
            
            return {
                'success': result.returncode == 0,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'test_log_file': str(test_log_file),
                'general_log_file': general_log_file
            }
            
        except subprocess.TimeoutExpired:
            error_msg = f"Test command timed out after 600 seconds"
            with open(test_log_file, 'w', encoding='utf-8') as f:
                f.write(f"Test Command: {command}\n")
                f.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                f.write(f"Exit Code: -1 (TIMEOUT)\n")
                f.write("=" * 80 + "\n")
                f.write("STDERR:\n")
                f.write(error_msg)
            
            return {
                'success': False,
                'exit_code': -1,
                'stdout': "",
                'stderr': error_msg,
                'test_log_file': str(test_log_file),
                'general_log_file': ""
            }
    
    def analyze_test_output(self, log_file: str) -> Dict[str, Any]:
        """Analyze test output and extract key information"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            analysis = {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'errors': 0,
                'skipped_tests': 0,
                'test_summary': "",
                'error_details': [],
                'success': False
            }
            
            # Look for test summary patterns
            lines = content.split('\n')
            for line in lines:
                if 'Ran' in line and 'test' in line:
                    analysis['test_summary'] = line.strip()
                    # Extract total tests
                    try:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part == 'Ran':
                                analysis['total_tests'] = int(parts[i + 1])
                                break
                    except (ValueError, IndexError):
                        pass
                
                elif 'FAILED' in line:
                    analysis['success'] = False
                    # Extract failure counts
                    try:
                        if 'failures=' in line:
                            parts = line.split('failures=')[1].split()[0]
                            analysis['failed_tests'] = int(parts)
                        if 'errors=' in line:
                            parts = line.split('errors=')[1].split()[0]
                            analysis['errors'] = int(parts)
                    except (ValueError, IndexError):
                        pass
                
                elif 'OK' in line and 'test' in line:
                    analysis['success'] = True
                    analysis['passed_tests'] = analysis['total_tests']
            
            # Extract error details
            error_sections = []
            current_error = ""
            in_error = False
            
            for line in lines:
                if line.startswith('=') and 'ERROR' in line:
                    in_error = True
                    current_error = line + "\n"
                elif in_error and line.startswith('='):
                    in_error = False
                    if current_error:
                        error_sections.append(current_error)
                        current_error = ""
                elif in_error:
                    current_error += line + "\n"
            
            analysis['error_details'] = error_sections
            
            return analysis
            
        except Exception as e:
            return {
                'error': f"Failed to analyze log file: {str(e)}",
                'success': False
            }

def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python log_output.py <command>")
        print("Examples:")
        print("  python log_output.py 'python manage.py test'")
        print("  python log_output.py 'python manage.py migrate'")
        return
    
    command = " ".join(sys.argv[1:])
    logger = OutputLogger()
    
    print(f"Running command: {command}")
    result = logger.run_and_log(command)
    
    if result['success']:
        print(f"✅ Command completed successfully")
    else:
        print(f"❌ Command failed with exit code {result['exit_code']}")
    
    print(f"📄 Output logged to: {result['log_file']}")
    
    if result['stderr']:
        print(f"⚠️  Errors: {result['stderr'][:200]}...")

if __name__ == "__main__":
    main() 