#!/usr/bin/env python3
"""
Simple endpoint test to verify current status
"""

import sys
sys.path.append('/home/engine/project')

# Test app startup
try:
    from app.main import app
    print("✅ App imports successfully")
    
    # Check routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    print(f"\n📋 Found {len(routes)} routes:")
    for route in sorted(routes):
        print(f"  {route}")
        
except Exception as e:
    print(f"❌ Error: {e}")