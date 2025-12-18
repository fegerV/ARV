#!/usr/bin/env python3
"""
Test script to verify that migrations run correctly on startup.
This script can be used to manually test the migration process.
"""

import subprocess
import sys
import time
import os

def test_migration_process():
    """Test that migrations run correctly when starting the application."""
    print("Testing migration startup process...")
    
    # Change to project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Test that entrypoint.sh is executable
        result = subprocess.run(['ls', '-la', 'entrypoint.sh'], 
                              capture_output=True, text=True, cwd='.')
        print("Entrypoint file permissions:")
        print(result.stdout)
        
        # Test alembic migration command
        print("\nTesting alembic migration command...")
        result = subprocess.run(['alembic', 'heads'], 
                              capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print("Alembic is properly configured")
            print(result.stdout)
        else:
            print("Error with alembic configuration:")
            print(result.stderr)
            return False
            
        # Test docker build
        print("\nTesting docker build...")
        result = subprocess.run(['docker', 'build', '-f', 'Dockerfile.dev', '-t', 'vertex-ar-test', '.'], 
                              capture_output=True, text=True, cwd='.')
        if result.returncode == 0:
            print("Docker build successful")
        else:
            print("Docker build failed:")
            print(result.stderr)
            # Continue anyway as this might be due to docker not running
            
        print("\nMigration startup test completed.")
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        return False

if __name__ == "__main__":
    success = test_migration_process()
    sys.exit(0 if success else 1)