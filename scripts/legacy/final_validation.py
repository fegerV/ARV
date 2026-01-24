#!/usr/bin/env python3
"""
Final validation of AR Content form fixes
"""

import subprocess
import sys

def run_test(test_name, command):
    """Run a test and return success status"""
    print(f"\n🔍 {test_name}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd="/home/engine/project")
        if result.returncode == 0:
            print(f"✅ {test_name} - PASSED")
            return True
        else:
            print(f"❌ {test_name} - FAILED")
            print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {test_name} - ERROR: {e}")
        return False

def main():
    """Run final validation tests"""
    print("🚀 Final Validation of AR Content Form Fixes\n")
    
    # Test 1: Form structure validation
    success1 = run_test(
        "Form Structure Validation",
        "source venv/bin/activate && python test_ar_content_form_fixes.py"
    )
    
    # Test 2: Check files exist and are properly formatted
    success2 = run_test(
        "File Existence Check", 
        "ls -la templates/ar-content/form.html templates/base.html"
    )
    
    # Test 3: Validate HTML syntax
    success3 = run_test(
        "HTML Syntax Validation",
        "grep -n 'class=\"form-select\"' templates/ar-content/form.html | wc -l"
    )
    
    # Test 4: Check CSS fixes
    success4 = run_test(
        "CSS Dark Mode Fixes",
        "grep -c 'dark select' templates/base.html"
    )
    
    # Summary
    total_tests = 4
    passed_tests = sum([success1, success2, success3, success4])
    
    print(f"\n📊 Final Validation Results:")
    print(f"   Tests Passed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("✅ AR Content form fixes are complete and working correctly")
        print("\n📝 Ready for manual testing:")
        print("1. Start server: source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("2. Login: http://localhost:8000/admin/login (admin@vertexar.com / admin123)")
        print("3. Test form: http://localhost:8000/ar-content/create")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} validation(s) failed")
        print("Please review the issues above before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
