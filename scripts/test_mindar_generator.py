#!/usr/bin/env python3
"""
Test script for MindAR marker generator Python integration
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.mindar_generator import mindar_generator

async def test_mindar_generator():
    """Test the MindAR marker generator"""
    print("Testing MindAR Marker Generator")
    print("=" * 40)
    
    # Test image path
    image_path = Path("valid_test_image.png")
    output_path = Path("/tmp/python_test_output.mind")
    
    if not image_path.exists():
        print(f"❌ Test image not found: {image_path}")
        return False
    
    print(f"📸 Input image: {image_path}")
    print(f"📤 Output path: {output_path}")
    
    try:
        # Test basic marker generation
        print("\n🔄 Starting marker generation...")
        result = await mindar_generator.generate_marker(
            image_path=image_path,
            output_path=output_path,
            max_features=500
        )
        
        if result["success"]:
            print("✅ Marker generation successful!")
            print(f"   📁 Marker path: {result['marker_path']}")
            print(f"   📏 File size: {result['file_size']} bytes")
            print(f"   📐 Dimensions: {result['width']}x{result['height']}")
            print(f"   🔢 Features: {result['features']}")
            
            # Verify output file exists
            if output_path.exists():
                print("✅ Output file created successfully")
                return True
            else:
                print("❌ Output file not found")
                return False
        else:
            print(f"❌ Marker generation failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_generate_and_upload():
    """Test the generate_and_upload_marker method"""
    print("\n🔄 Testing generate_and_upload_marker...")
    
    try:
        result = await mindar_generator.generate_and_upload_marker(
            ar_content_id="test-123",
            image_path=Path("valid_test_image.png"),
            max_features=500
        )
        
        if result["success"]:
            print("✅ Generate and upload successful!")
            print(f"   📁 Marker path: {result['marker_path']}")
            print(f"   📏 File size: {result['file_size']} bytes")
            print(f"   📐 Dimensions: {result['width']}x{result['height']}")
            print(f"   🔢 Features: {result['features']}")
            print(f"   🌐 Marker URL: {result.get('marker_url', 'N/A')}")
            print(f"   📦 Storage path: {result.get('storage_path', 'N/A')}")
            return True
        else:
            print(f"❌ Generate and upload failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during upload testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("MindAR Generator Integration Test")
    print("=" * 50)
    
    # Test 1: Basic marker generation
    test1_result = await test_mindar_generator()
    
    # Test 2: Generate and upload
    test2_result = await test_generate_and_upload()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"🧪 Basic Generation: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"🚀 Generate & Upload: {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! MindAR generator is working correctly.")
        return True
    else:
        print("\n💥 Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)