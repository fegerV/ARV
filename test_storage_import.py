#!/usr/bin/env python3
"""
Test script to verify new storage provider imports and functionality
"""

import sys
import tempfile
import shutil
import asyncio
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

async def test_storage_functionality():
    """Test storage provider functionality."""
    try:
        print("Testing new storage provider imports...")
        
        # Test new storage provider module
        from app.core.storage_providers import StorageProvider, LocalStorageProvider, get_storage_provider
        print("✓ Successfully imported new storage provider classes")
        
        # Test storage module (backward compatibility)
        from app.core.storage import (
            save_file_to_storage, 
            get_file_from_storage, 
            delete_file_from_storage,
            check_file_exists,
            get_public_file_url,
            get_storage_usage_stats
        )
        print("✓ Successfully imported backward compatibility functions")
        
        # Test configuration
        from app.core.config import settings
        print(f"✓ Local storage path: {settings.LOCAL_STORAGE_PATH}")
        print(f"✓ Local storage public URL: {settings.LOCAL_STORAGE_PUBLIC_URL}")
        
        # Test provider instantiation
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = LocalStorageProvider(
                base_path=temp_dir,
                public_url_base="http://test.com/storage"
            )
            print("✓ Successfully created LocalStorageProvider instance")
            
            # Test basic functionality
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Hello, World!")
            
            # Save file
            url = await provider.save_file(str(test_file), "saved/test.txt")
            print(f"✓ Successfully saved file: {url}")
            
            # Check file exists
            exists = await provider.file_exists("saved/test.txt")
            print(f"✓ File exists check: {exists}")
            
            # Get usage stats
            stats = await provider.get_usage_stats()
            print(f"✓ Usage stats: {stats['total_files']} files, {stats['total_size_bytes']} bytes")
            
            # Delete file
            deleted = await provider.delete_file("saved/test.txt")
            print(f"✓ File deleted: {deleted}")
        
        print("\n🎉 All storage provider tests passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_storage_functionality())