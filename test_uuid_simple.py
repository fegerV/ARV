#!/usr/bin/env python3
"""
Simple test to verify UUID utility functions work with strings.
"""
import uuid
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_uuid_utilities():
    """Test UUID utility functions without database dependencies."""
    print("Testing UUID utility functions...")
    
    # Import the functions we fixed
    try:
        from app.utils.ar_content import (
            build_ar_content_storage_path,
            build_unique_link
        )
        print("✓ Successfully imported utility functions")
    except Exception as e:
        print(f"✗ Failed to import utility functions: {e}")
        return False
    
    # Test with string UUID
    string_uuid = str(uuid.uuid4())
    print(f"Using string UUID: {string_uuid}")
    
    # Test build_ar_content_storage_path
    try:
        path = build_ar_content_storage_path(1, "project-1", string_uuid)
        print(f"✓ build_ar_content_storage_path: {path}")
        print(f"  Path type: {type(path)}")
    except Exception as e:
        print(f"✗ build_ar_content_storage_path failed: {e}")
        return False
    
    # Test build_unique_link
    try:
        link = build_unique_link(string_uuid)
        print(f"✓ build_unique_link: {link}")
        print(f"  Link type: {type(link)}")
    except Exception as e:
        print(f"✗ build_unique_link failed: {e}")
        return False
    
    return True


def test_import_changes():
    """Test that our changes are properly applied."""
    print("\nTesting import changes...")
    
    # Check that we can import without uuid module in ar_content utils
    try:
        import app.utils.ar_content as utils
        print("✓ app.utils.ar_content imported successfully")
        
        # Check function signatures
        import inspect
        
        # Check build_ar_content_storage_path signature
        sig = inspect.signature(build_ar_content_storage_path)
        params = list(sig.parameters.keys())
        print(f"  build_ar_content_storage_path params: {params}")
        
        # Check build_unique_link signature  
        sig = inspect.signature(build_unique_link)
        params = list(sig.parameters.keys())
        print(f"  build_unique_link params: {params}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("UUID COMPATIBILITY TEST - SIMPLE VERSION")
    print("=" * 50)
    
    success = True
    
    if not test_import_changes():
        success = False
    
    if not test_uuid_utilities():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("UUID compatibility changes are working correctly.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the errors above.")
    print("=" * 50)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)