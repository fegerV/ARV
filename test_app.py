#!/usr/bin/env python3
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from app.main import app
    print("OK: App loaded successfully")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
