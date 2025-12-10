#!/usr/bin/env python3
"""
Test script to verify thumbnail service imports and basic functionality
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

try:
    print("Testing thumbnail service imports...")
    
    # Test thumbnail service
    from app.services.thumbnail_service import ThumbnailService, thumbnail_service
    print("✓ Successfully imported ThumbnailService")
    
    # Test basic instantiation
    service = ThumbnailService()
    print("✓ Successfully instantiated ThumbnailService")
    
    # Test attributes
    assert hasattr(service, 'thumbnail_size')
    assert hasattr(service, 'quality')
    print("✓ ThumbnailService has required attributes")
    
    # Test singleton
    assert thumbnail_service is not None
    print("✓ Successfully accessed thumbnail_service singleton")
    
    print("\n🎉 All thumbnail service imports and basic tests successful!")
    
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