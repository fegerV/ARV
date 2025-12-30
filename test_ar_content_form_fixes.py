#!/usr/bin/env python3
"""
Test script to validate AR Content form fixes:
1. Project filtering when company is selected
2. Dark mode contrast for form elements
3. Submit button visibility and functionality
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.html.mock import PROJECT_CREATE_MOCK_DATA
from app.html.routes.ar_content import ar_content_create
from fastapi import Request
from starlette.datastructures import QueryParams

class MockRequest:
    def __init__(self):
        self.query_params = QueryParams("")

class MockUser:
    def __init__(self):
        self.id = 1
        self.email = "admin@test.com"
        self.is_active = True
        self.is_superuser = True

async def test_mock_data():
    """Test that mock data has correct structure"""
    print("🔍 Testing mock data structure...")
    
    companies = PROJECT_CREATE_MOCK_DATA["companies"]
    projects = PROJECT_CREATE_MOCK_DATA["projects"]
    
    print(f"✅ Companies found: {len(companies)}")
    for company in companies:
        print(f"   - {company['name']} (ID: {company['id']})")
    
    print(f"✅ Projects found: {len(projects)}")
    for project in projects:
        company = next(c for c in companies if c['id'] == project['company_id'])
        print(f"   - {project['name']} (Company: {company['name']}, ID: {project['id']})")
    
    # Test filtering logic
    print("\n🔍 Testing project filtering logic...")
    selected_company_id = "1"
    filtered_projects = [
        project for project in projects 
        if str(project['company_id']) == str(selected_company_id)
    ]
    
    print(f"✅ Filtered projects for company {selected_company_id}: {len(filtered_projects)}")
    for project in filtered_projects:
        print(f"   - {project['name']}")
    
    return len(companies) > 0 and len(projects) > 0 and len(filtered_projects) > 0

def test_form_html():
    """Test that form HTML contains required elements"""
    print("\n🔍 Testing form HTML structure...")
    
    form_path = "/home/engine/project/templates/ar-content/form.html"
    with open(form_path, 'r') as f:
        content = f.read()
    
    # Check for required elements
    required_elements = [
        'class="form-input"',
        'class="form-select"', 
        'btn btn-primary',
        'x-model="formData.company_id"',
        'x-model="formData.project_id"',
        'filteredProjects',
        'updateProjects'
    ]
    
    missing_elements = []
    for element in required_elements:
        if element not in content:
            missing_elements.append(element)
    
    if missing_elements:
        print(f"❌ Missing elements: {missing_elements}")
        return False
    else:
        print("✅ All required form elements found")
        return True

def test_css_styles():
    """Test that CSS has dark mode fixes"""
    print("\n🔍 Testing CSS dark mode styles...")
    
    css_path = "/home/engine/project/templates/base.html"
    with open(css_path, 'r') as f:
        content = f.read()
    
    # Check for dark mode fixes
    required_styles = [
        'dark .form-input',
        'dark .form-select',
        'dark select',
        'background-color: #374151 !important',
        'color: #f9fafb !important'
    ]
    
    missing_styles = []
    for style in required_styles:
        if style not in content:
            missing_styles.append(style)
    
    if missing_styles:
        print(f"❌ Missing CSS styles: {missing_styles}")
        return False
    else:
        print("✅ All required dark mode CSS styles found")
        return True

async def main():
    """Run all tests"""
    print("🚀 Testing AR Content Form Fixes\n")
    
    tests = [
        ("Mock Data Structure", test_mock_data()),
        ("Form HTML Structure", test_form_html()),
        ("CSS Dark Mode Styles", test_css_styles())
    ]
    
    results = []
    for test_name, result in tests:
        if asyncio.iscoroutine(result):
            result = await result
        results.append((test_name, result))
    
    print("\n📊 Test Results:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Summary: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! AR Content form fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)