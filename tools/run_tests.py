#!/usr/bin/env python
"""
Test runner wrapper for clean output capture.
This script runs pytest and writes output to a file, solving PowerShell encoding issues.

Usage:
    python tools/run_tests.py              # Run all tests
    python tools/run_tests.py -q           # Quiet mode
    python tools/run_tests.py tests/unit/  # Run specific tests
    python tools/run_tests.py -x           # Stop on first failure
"""
import subprocess
import sys
import os

def main():
    # Build pytest command
    pytest_args = [sys.executable, '-m', 'pytest']
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    else:
        # Default: run all tests with short output
        pytest_args.extend(['tests/', '--tb=short', '-q'])
    
    # Run pytest
    result = subprocess.run(
        pytest_args,
        capture_output=True,
        text=True,
        encoding='utf-8',
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    
    # Write to file for agent reading
    output_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'test_output.txt'
    )
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write('\n--- STDERR ---\n')
            f.write(result.stderr)
    
    # Also print to console for humans
    print(result.stdout)
    if result.stderr:
        print('--- STDERR ---', file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    # Print summary
    print(f'\n📁 Full output saved to: test_output.txt')
    
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
