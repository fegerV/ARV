#!/usr/bin/env python3
"""
Test script to simulate browser interaction with AR content creation
"""
import asyncio
import httpx
import json
from bs4 import BeautifulSoup


async def test_ar_content_create():
    """Test AR content creation flow"""
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(follow_redirects=False) as client:
        print("=== Testing AR Content Creation Flow ===")
        
        # Step 1: Try to access AR content create page (should redirect to login)
        print("\n1. Testing unauthorized access to /ar-content/create")
        response = await client.get(f"{base_url}/ar-content/create")
        print(f"Status: {response.status_code}")
        if response.status_code == 303:
            print("✅ Correctly redirected to login")
        
        # Step 2: Login
        print("\n2. Logging in as admin")
        login_data = {
            "username": "admin@vertexar.com",
            "password": "admin123"
        }
        
        # First get the login page to get cookies
        login_page = await client.get(f"{base_url}/admin/login")
        print(f"Login page status: {login_page.status_code}")
        
        # Submit login form
        login_response = await client.post(
            f"{base_url}/admin/login-form",
            data=login_data,
            follow_redirects=False
        )
        print(f"Login response status: {login_response.status_code}")
        
        if login_response.status_code in [302, 303]:
            print("✅ Login successful, redirected")
            # Extract cookies from login response
            cookies = login_response.cookies
            
            # Step 3: Access admin dashboard first
            print("\n3. Testing access to admin dashboard")
            dashboard_response = await client.get(f"{base_url}/admin", cookies=cookies)
            print(f"Dashboard status: {dashboard_response.status_code}")
            
            # Step 4: Access AR content create page with cookies
            print("\n4. Accessing /ar-content/create after login")
            create_response = await client.get(f"{base_url}/ar-content/create", cookies=cookies)
            print(f"Create page status: {create_response.status_code}")
            
            if create_response.status_code == 200:
                print("✅ Successfully accessed AR content creation page")
                
                # Parse HTML to check if data is present
                soup = BeautifulSoup(create_response.text, 'html.parser')
                
                # Check for companies and projects data
                scripts = soup.find_all('script')
                data_found = False
                
                for script in scripts:
                    if script.string and 'companies_js' in script.string:
                        print("✅ Found companies_js data in template")
                        data_found = True
                        
                        # Extract and analyze the data
                        try:
                            # Find the arContentForm call
                            import re
                            pattern = r'arContentForm\([^,]+,\s*(\[.*?\]),\s*(\[.*?\])'
                            match = re.search(pattern, script.string)
                            if match:
                                companies_data = match.group(1)
                                projects_data = match.group(2)
                                
                                print(f"Companies data: {companies_data[:200]}...")
                                print(f"Projects data: {projects_data[:200]}...")
                                
                                # Parse JSON to verify structure
                                try:
                                    companies = json.loads(companies_data)
                                    projects = json.loads(projects_data)
                                    
                                    print(f"✅ Parsed {len(companies)} companies")
                                    print(f"✅ Parsed {len(projects)} projects")
                                    
                                    for company in companies:
                                        print(f"  Company: {company.get('name')} (ID: {company.get('id')})")
                                    
                                    for project in projects:
                                        print(f"  Project: {project.get('name')} (ID: {project.get('id')}, Company ID: {project.get('company_id')})")
                                        
                                except json.JSONDecodeError as e:
                                    print(f"❌ Failed to parse JSON: {e}")
                        except Exception as e:
                            print(f"❌ Error analyzing data: {e}")
                
                if not data_found:
                    print("❌ No companies_js data found in template")
            else:
                print(f"❌ Failed to access create page: {create_response.status_code}")
        else:
            print("❌ Login failed")


if __name__ == "__main__":
    asyncio.run(test_ar_content_create())