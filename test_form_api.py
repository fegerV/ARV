#!/usr/bin/env python3
"""
Test AR Content Form - Direct API test
"""

import asyncio
import aiohttp
import json

async def test_form_api():
    """Test the form API endpoint directly"""
    
    print("🔍 Testing AR Content Form API...")
    
    async with aiohttp.ClientSession() as session:
        # Test the API endpoint that provides form data
        async with session.get("http://localhost:8000/api/companies") as response:
            if response.status == 200:
                companies = await response.json()
                print(f"✅ Found {len(companies)} companies")
                for company in companies:
                    print(f"   - {company['name']} (ID: {company['id']})")
            else:
                print(f"❌ Companies API failed: {response.status}")
                return
        
        async with session.get("http://localhost:8000/api/projects") as response:
            if response.status == 200:
                projects = await response.json()
                print(f"✅ Found {len(projects)} projects")
                for project in projects:
                    print(f"   - {project['name']} (ID: {project['id']}, company_id: {project['company_id']})")
            else:
                print(f"❌ Projects API failed: {response.status}")
                return

if __name__ == "__main__":
    asyncio.run(test_form_api())