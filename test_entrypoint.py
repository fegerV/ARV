#!/usr/bin/env python3
"""
Test script to verify entrypoint.sh functionality
"""

import os
import subprocess
import sys

def test_entrypoint():
    """Test that entrypoint.sh has the right content and permissions"""
    print("Testing entrypoint.sh...")
    
    # Check if entrypoint.sh exists
    if not os.path.exists('entrypoint.sh'):
        print("ERROR: entrypoint.sh not found")
        return False
    
    # Read the file content
    with open('entrypoint.sh', 'r') as f:
        content = f.read()
    
    # Check for required elements
    required_elements = [
        '#!/bin/bash',
        'set -e',
        'alembic upgrade head',
        'exec "$@"'
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"ERROR: Missing elements in entrypoint.sh: {missing_elements}")
        return False
    
    # Check if file is executable
    try:
        result = subprocess.run(['ls', '-l', 'entrypoint.sh'], 
                              capture_output=True, text=True, cwd='.')
        if '-rwx' not in result.stdout:
            print("WARNING: entrypoint.sh may not be executable")
            print("Please run: chmod +x entrypoint.sh")
    except Exception as e:
        print(f"WARNING: Could not check file permissions: {e}")
    
    print("SUCCESS: entrypoint.sh appears to be correctly configured")
    return True

if __name__ == "__main__":
    success = test_entrypoint()
    sys.exit(0 if success else 1)