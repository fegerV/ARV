#!/usr/bin/env python3
"""Quick test to check if app can be imported."""
import sys
import os

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from app.main import app
    print("OK: App loaded successfully")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
