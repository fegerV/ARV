#!/usr/bin/env python3
"""
Debug AR Content Form Template
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app

def debug_form_template():
    """Debug the form template"""
    print("🔍 Debugging AR Content Form Template...")
    
    client = TestClient(app)
    
    # Get the create form page
    response = client.get("/ar-content/create")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        html_content = response.text
        
        # Save the HTML to a file for inspection
        with open("debug_form.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print("✅ HTML content saved to debug_form.html")
        
        # Check for specific elements
        checks = {
            "Photo file input": 'id="photo_file"' in html_content,
            "Video file input": 'id="video_file"' in html_content,
            "Company dropdown": 'id="company_id"' in html_content,
            "Project dropdown": 'id="project_id"' in html_content,
            "Alpine.js x-data": 'x-data="arContentForm"' in html_content,
            "Form tag": '<form' in html_content,
            "Multipart form": 'enctype="multipart/form-data"' in html_content,
            "JavaScript function": 'function arContentForm' in html_content
        }
        
        print("\n📋 Element Checks:")
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"{status} {check_name}: {result}")
        
        # Look for the file input elements specifically
        print("\n🔍 Looking for file input elements...")
        lines = html_content.split('\n')
        for i, line in enumerate(lines):
            if 'input' in line and 'type="file"' in line:
                print(f"Line {i+1}: {line.strip()}")
        
        # Look for JavaScript
        print("\n🔍 Looking for JavaScript...")
        in_script = False
        script_lines = []
        for line in lines:
            if '<script>' in line:
                in_script = True
            if in_script:
                script_lines.append(line)
            if '</script>' in line:
                in_script = False
                break
        
        if script_lines:
            print("Found JavaScript in template:")
            for line in script_lines:
                print(f"  {line}")
        else:
            print("❌ No JavaScript found in template")
            
    else:
        print(f"❌ Failed to get form page: {response.status_code}")
        print(f"Response: {response.text[:500]}")

if __name__ == "__main__":
    debug_form_template()