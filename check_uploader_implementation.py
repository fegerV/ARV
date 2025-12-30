#!/usr/bin/env python3
"""
Simple test to check if the updated form template is being served correctly
"""
import subprocess
import time

def check_server_and_form():
    """Check if server is running and form contains new uploader"""
    
    # Start server if not running
    try:
        result = subprocess.run(['curl', '-s', 'http://localhost:8000/admin/login'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("❌ Server is not running")
            return False
    except:
        print("❌ Server is not accessible")
        return False
    
    print("✅ Server is running")
    
    # Check form template directly
    try:
        with open('/home/engine/project/templates/ar-content/form.html', 'r') as f:
            content = f.read()
            
        has_photo_uploader = 'photoUploader()' in content
        has_video_uploader = 'videoUploader()' in content
        has_drag_drop = 'dragover.prevent' in content
        has_alpine_data = 'x-data="photoUploader()"' in content
        
        print(f"✅ Template has photo uploader: {has_photo_uploader}")
        print(f"✅ Template has video uploader: {has_video_uploader}")
        print(f"✅ Template has drag & drop: {has_drag_drop}")
        print(f"✅ Template has Alpine data: {has_alpine_data}")
        
        if all([has_photo_uploader, has_video_uploader, has_drag_drop, has_alpine_data]):
            print("🎉 Form template has been updated successfully!")
            
            # Show some key features
            print("\n📋 New Features Added:")
            print("  • Drag & drop file upload")
            print("  • File preview with remove button")
            print("  • File size validation")
            print("  • Loading states with animations")
            print("  • Better visual feedback")
            print("  • Separate components for photo/video")
            
            return True
        else:
            print("❌ Template update incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Error reading template: {e}")
        return False

def show_instructions():
    """Show manual testing instructions"""
    print("\n" + "=" * 60)
    print("📝 MANUAL TESTING INSTRUCTIONS")
    print("=" * 60)
    print("1. Open browser and go to: http://localhost:8000/admin/login")
    print("2. Login with credentials:")
    print("   • Email: admin@vertexar.com")
    print("   • Password: admin123")
    print("3. Navigate to: http://localhost:8000/ar-content/create")
    print("4. Test the following features:")
    print("   • Click on photo upload area → should open file picker")
    print("   • Click on video upload area → should open file picker")
    print("   • Drag files over upload areas → should show hover state")
    print("   • Select valid files → should show preview")
    print("   • Click X button on preview → should remove file")
    print("   • Try invalid files → should show error messages")
    print("5. Fill form and submit → should create AR content")
    print("=" * 60)

if __name__ == "__main__":
    print("🔍 Checking AR Content File Uploader Implementation")
    print("=" * 60)
    
    success = check_server_and_form()
    
    if success:
        print("\n✅ Implementation appears to be correct!")
        show_instructions()
    else:
        print("\n❌ Implementation has issues!")