#!/usr/bin/env python3
"""
Simple test server for admin interface testing.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for testing
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_vertex_ar.db")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-admin-testing")
os.environ.setdefault("MEDIA_ROOT", "./test_storage/content")
os.environ.setdefault("STORAGE_BASE_PATH", "./test_storage/content")
os.environ.setdefault("LOCAL_STORAGE_PATH", "./test_storage/content")
os.environ.setdefault("TEMPLATES_DIR", "./templates")
os.environ.setdefault("STATIC_DIR", "./static")

def main():
    """Main function to start the server."""
    print("🚀 Starting simple test server for admin interface...")
    
    print("\n📝 Server Information:")
    print("🌐 URL: http://localhost:8000")
    print("🔐 Admin Login: http://localhost:8000/admin/login")
    print("👤 Email: admin@vertexar.com")
    print("🔑 Password: admin123")
    print("\n⚠️  Press Ctrl+C to stop the server")
    
    # Start the server
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()