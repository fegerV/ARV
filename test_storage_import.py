#!/usr/bin/env python3
"""
Test script to verify storage provider imports
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    print("Testing storage provider imports...")
    
    # Test base module
    from app.services.storage.base import StorageProvider
    print("✓ Successfully imported StorageProvider base class")
    
    # Test factory
    from app.services.storage.factory import get_provider
    print("✓ Successfully imported get_provider factory function")
    
    # Test providers
    from app.services.storage.local_provider import LocalStorageProvider
    print("✓ Successfully imported LocalStorageProvider")
    
    from app.services.storage.minio_provider import MinioStorageProvider
    print("✓ Successfully imported MinioStorageProvider")
    
    from app.services.storage.yandex_disk_provider import YandexDiskProvider
    print("✓ Successfully imported YandexDiskProvider")
    
    print("\n🎉 All storage provider imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)