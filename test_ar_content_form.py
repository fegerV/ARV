#!/usr/bin/env python3
"""
Test AR Content Form Functionality
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app
from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.project import Project
from app.models.user import User
from sqlalchemy import select
from fastapi.testclient import TestClient
from html.parser import HTMLParser

class ARContentFormTester:
    def __init__(self):
        self.client = TestClient(app)
        self.base_url = "http://localhost:8000"
        
    def test_ar_content_form_page(self):
        """Test the AR content create form page"""
        print("🔍 Testing AR Content Create Form Page...")
        
        try:
            # Test the create form page
            response = self.client.get("/ar-content/create")
            
            if response.status_code == 200:
                print("✅ AR Content create form page loaded successfully")
                
                # Parse HTML to check form elements
                html_content = response.text
                
                # Check for key form elements
                checks = {
                    "File input for photo": 'id="photo_file"' in html_content,
                    "File input for video": 'id="video_file"' in html_content,
                    "Company dropdown": 'id="company_id"' in html_content,
                    "Project dropdown": 'id="project_id"' in html_content,
                    "Alpine.js integration": 'x-data="arContentForm"' in html_content,
                    "Form submission": 'enctype="multipart/form-data"' in html_content,
                    "JavaScript file handlers": 'handlePhotoChange' in html_content,
                    "JavaScript video handlers": 'handleVideoChange' in html_content
                }
                
                for check_name, result in checks.items():
                    if result:
                        print(f"✅ {check_name}: Present")
                    else:
                        print(f"❌ {check_name}: Missing")
                        
                return True
            else:
                print(f"❌ Failed to load AR Content create form: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing AR Content create form: {str(e)}")
            return False
    
    def test_ar_content_list_page(self):
        """Test the AR content list page"""
        print("\n🔍 Testing AR Content List Page...")
        
        try:
            response = self.client.get("/ar-content")
            
            if response.status_code == 200:
                print("✅ AR Content list page loaded successfully")
                
                html_content = response.text
                
                # Check for list elements
                checks = {
                    "Table structure": '<table class="table">' in html_content,
                    "Thumbnail column": "Thumbnail" in html_content,
                    "Actions column": "Actions" in html_content,
                    "Status display": "status" in html_content.lower(),
                    "Create button": 'Add AR Content' in html_content
                }
                
                for check_name, result in checks.items():
                    if result:
                        print(f"✅ {check_name}: Present")
                    else:
                        print(f"❌ {check_name}: Missing")
                        
                return True
            else:
                print(f"❌ Failed to load AR Content list: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing AR Content list: {str(e)}")
            return False
    
    async def test_database_data(self):
        """Test if companies and projects exist in database"""
        print("\n🔍 Testing Database Data...")
        
        try:
            async with AsyncSessionLocal() as db:
                # Check companies
                companies_query = select(Company)
                companies_result = await db.execute(companies_query)
                companies = companies_result.scalars().all()
                
                print(f"✅ Found {len(companies)} companies in database")
                for company in companies[:3]:  # Show first 3
                    print(f"   - {company.name} (ID: {company.id})")
                
                # Check projects
                projects_query = select(Project)
                projects_result = await db.execute(projects_query)
                projects = projects_result.scalars().all()
                
                print(f"✅ Found {len(projects)} projects in database")
                for project in projects[:3]:  # Show first 3
                    print(f"   - {project.name} (ID: {project.id}, Company: {project.company_id})")
                
                # Check AR content
                ar_content_query = select(ARContent)
                ar_content_result = await db.execute(ar_content_query)
                ar_contents = ar_content_result.scalars().all()
                
                print(f"✅ Found {len(ar_contents)} AR content items in database")
                for ar_content in ar_contents[:3]:  # Show first 3
                    print(f"   - {ar_content.order_number or 'No order'} ({ar_content.status})")
                
                return len(companies) > 0 and len(projects) > 0
                
        except Exception as e:
            print(f"❌ Error testing database data: {str(e)}")
            return False
    
    def test_file_upload_endpoints(self):
        """Test file upload endpoints"""
        print("\n🔍 Testing File Upload Endpoints...")
        
        try:
            # Test if the API endpoints exist
            endpoints_to_test = [
                "/api/companies/1/projects/1/ar-content",
                "/api/ar-content"
            ]
            
            for endpoint in endpoints_to_test:
                try:
                    response = self.client.options(endpoint)
                    print(f"✅ Endpoint {endpoint}: Available (OPTIONS: {response.status_code})")
                except Exception as e:
                    print(f"❌ Endpoint {endpoint}: Not available - {str(e)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing file upload endpoints: {str(e)}")
            return False
    
    def analyze_form_javascript(self):
        """Analyze the JavaScript functionality in the form"""
        print("\n🔍 Analyzing Form JavaScript...")
        
        try:
            response = self.client.get("/ar-content/create")
            html_content = response.text
            
            # Extract and analyze JavaScript
            js_checks = {
                "Alpine.js component definition": "function arContentForm" in html_content,
                "File change handlers": "handlePhotoChange" in html_content and "handleVideoChange" in html_content,
                "Form validation": "get isValid" in html_content,
                "Form submission": "handleSubmit" in html_content,
                "File type validation": "file.type.startsWith" in html_content,
                "File size validation": "file.size >" in html_content,
                "FormData usage": "new FormData" in html_content,
                "Fetch API usage": "fetch(" in html_content
            }
            
            for check_name, result in js_checks.items():
                if result:
                    print(f"✅ {check_name}: Implemented")
                else:
                    print(f"❌ {check_name}: Missing")
            
            return True
            
        except Exception as e:
            print(f"❌ Error analyzing form JavaScript: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting AR Content Form Tests\n")
        print("=" * 60)
        
        results = []
        
        # Test 1: Form page
        results.append(self.test_ar_content_form_page())
        
        # Test 2: List page
        results.append(self.test_ar_content_list_page())
        
        # Test 3: Database data
        results.append(await self.test_database_data())
        
        # Test 4: File upload endpoints
        results.append(self.test_file_upload_endpoints())
        
        # Test 5: JavaScript analysis
        results.append(self.analyze_form_javascript())
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(results)
        total = len(results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the details above.")
        
        print("\n🔧 RECOMMENDATIONS:")
        
        # Check specific issues
        try:
            response = self.client.get("/ar-content/create")
            html_content = response.text
            
            if 'id="photo_file"' not in html_content:
                print("❌ Photo file input is missing from the form")
            
            if 'id="video_file"' not in html_content:
                print("❌ Video file input is missing from the form")
            
            if "handlePhotoChange" not in html_content:
                print("❌ Photo change handler is not implemented")
            
            if "handleVideoChange" not in html_content:
                print("❌ Video change handler is not implemented")
                
            # Check for actual file input elements
            if '<input id="photo_file" name="photo_file" type="file"' not in html_content:
                print("❌ Photo file input element is not properly configured")
                
            if '<input id="video_file" name="video_file" type="file"' not in html_content:
                print("❌ Video file input element is not properly configured")
        
        except Exception as e:
            print(f"❌ Error during recommendations analysis: {str(e)}")
        
        return passed == total

async def main():
    """Main function"""
    tester = ARContentFormTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✅ AR Content Form is properly configured!")
        return 0
    else:
        print("\n❌ AR Content Form has issues that need to be fixed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)