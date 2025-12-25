#!/usr/bin/env python3
"""
Simple test for MindAR marker generator without full dependencies
"""
import asyncio
import subprocess
import json
from pathlib import Path

async def test_mindar_compiler_direct():
    """Test the MindAR compiler directly via subprocess"""
    print("Testing MindAR Compiler Directly")
    print("=" * 40)
    
    # Test image path
    image_path = "valid_test_image.png"
    output_path = "/tmp/direct_test_output.mind"
    
    if not Path(image_path).exists():
        print(f"❌ Test image not found: {image_path}")
        return False
    
    print(f"📸 Input image: {image_path}")
    print(f"📤 Output path: {output_path}")
    
    try:
        # Run Node.js compiler script directly
        cmd = [
            "node",
            "app/services/mindar_compiler.js",
            image_path,
            output_path,
            "500"
        ]
        
        print("\n🔄 Running MindAR compiler...")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stdout_text = stdout.decode() if stdout else ""
        stderr_text = stderr.decode() if stderr else ""
        
        print(f"📤 Return code: {process.returncode}")
        print(f"📤 STDOUT: {stdout_text}")
        if stderr_text:
            print(f"📤 STDERR: {stderr_text}")
        
        if process.returncode == 0:
            # Check if output file was created
            if Path(output_path).exists():
                file_size = Path(output_path).stat().st_size
                print(f"✅ Marker generated successfully!")
                print(f"   📁 File size: {file_size} bytes")
                
                # Try to parse the result
                try:
                    lines = stdout_text.strip().split('\n')
                    for line in reversed(lines):
                        if line.startswith('{') and line.endswith('}'):
                            result = json.loads(line)
                            print(f"   📐 Dimensions: {result.get('width', 'N/A')}x{result.get('height', 'N/A')}")
                            print(f"   🔢 Features: {result.get('features', 'N/A')}")
                            break
                except json.JSONDecodeError:
                    print("   ⚠️  Could not parse result JSON")
                
                return True
            else:
                print("❌ Output file not created")
                return False
        else:
            print(f"❌ Compiler failed with return code {process.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mindar_file_structure():
    """Test the generated MindAR file structure"""
    print("\nTesting Generated MindAR File Structure")
    print("=" * 40)
    
    output_path = "/tmp/direct_test_output.mind"
    
    if not Path(output_path).exists():
        print(f"❌ Marker file not found: {output_path}")
        return False
    
    try:
        # Load and validate the JSON structure
        with open(output_path, 'r') as f:
            data = json.load(f)
        
        print("✅ JSON file loaded successfully")
        
        # Validate required fields
        required_fields = ["version", "type", "width", "height", "trackingData"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        print("✅ All required fields present")
        print(f"   📋 Version: {data['version']}")
        print(f"   📋 Type: {data['type']}")
        print(f"   📋 Dimensions: {data['width']}x{data['height']}")
        print(f"   📋 Tracking data: {type(data['trackingData'])}")
        
        # Validate tracking data structure
        if isinstance(data['trackingData'], list) and len(data['trackingData']) > 0:
            tracking_item = data['trackingData'][0]
            if 'data' in tracking_item:
                print(f"   📋 Tracking data points: {len(tracking_item['data'])}")
                print("✅ Tracking data structure valid")
            else:
                print("❌ Tracking data missing 'data' field")
                return False
        else:
            print("❌ Invalid tracking data structure")
            return False
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating file: {e}")
        return False

async def main():
    """Main test function"""
    print("MindAR Generator Test Suite")
    print("=" * 50)
    
    # Test 1: Direct compiler test
    test1_result = await test_mindar_compiler_direct()
    
    # Test 2: File structure validation
    test2_result = await test_mindar_file_structure()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Results Summary:")
    print(f"🧪 Compiler Test: {'✅ PASS' if test1_result else '❌ FAIL'}")
    print(f"📄 File Structure: {'✅ PASS' if test2_result else '❌ FAIL'}")
    
    if test1_result and test2_result:
        print("\n🎉 All tests passed! MindAR generator is working correctly.")
        print("\n📋 Summary:")
        print("   ✅ Node.js MindAR compiler functional")
        print("   ✅ Image processing working")
        print("   ✅ Feature extraction successful")
        print("   ✅ JSON marker file format valid")
        print("   ✅ Tracking data properly structured")
        return True
    else:
        print("\n💥 Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)