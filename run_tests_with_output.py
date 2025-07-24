#!/usr/bin/env python3
"""
Script to run the full test suite and capture output to a text file.
"""

import subprocess
import sys
import os
from datetime import datetime

def run_tests_with_output():
    """Run the test suite and capture all output to a file."""
    
    # Create output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_output_{timestamp}.txt"
    
    print(f"Running test suite and capturing output to: {output_file}")
    print("=" * 60)
    
    # Command to run the tests
    cmd = [sys.executable, "-m", "pytest", "test_all_phases.py", "-v", "--tb=long"]
    
    try:
        # Run the command and capture all output
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"Test Suite Output - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Command: {' '.join(cmd)}\n\n")
            f.flush()
            
            # Run the process and capture output in real-time
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Read output line by line and write to both console and file
            for line in iter(process.stdout.readline, ''):
                print(line.rstrip())
                f.write(line)
                f.flush()
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Write summary
            f.write(f"\n" + "=" * 60 + "\n")
            f.write(f"Process completed with return code: {return_code}\n")
            f.write(f"Output saved to: {output_file}\n")
            
            print(f"\n" + "=" * 60)
            print(f"Process completed with return code: {return_code}")
            print(f"Full output saved to: {output_file}")
            
            return return_code, output_file
            
    except Exception as e:
        error_msg = f"Error running tests: {e}"
        print(error_msg)
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(f"\nERROR: {error_msg}\n")
        return 1, output_file

if __name__ == "__main__":
    exit_code, output_file = run_tests_with_output()
    sys.exit(exit_code) 