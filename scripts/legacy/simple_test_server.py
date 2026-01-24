#!/usr/bin/env python3
"""
Simple test server to check admin interface without database.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for testing
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_vertex_ar.db")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-admin-testing")

def main():
    """Main function to start server."""
    print("🚀 Starting simple test server for admin interface...")
    
    print("\n📝 Server Information:")
    print("🌐 URL: http://localhost:8000")
    print("🔐 Admin Login: http://localhost:8000/admin/login")
    print("\n🎯 Testing Checklist:")
    print("1. Login page loads with proper styles")
    print("2. Theme toggle works (🌙/☀️)")
    print("3. Dark mode applies correctly")
    print("4. No white text on white background")
    print("\n⚠️  Press Ctrl+C to stop the server")
    
    # Start server
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
