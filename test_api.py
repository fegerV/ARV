import requests
import os

# URL API
BASE_URL = "http://localhost:8000"

# Данные для теста
COMPANY_ID = 2  # Test Company 2
PROJECT_ID = 1  # Test Project

def test_create_ar_content():
    """Тест создания AR контента с изображением"""
    url = f"{BASE_URL}/api/ar-content"
    
    # Подготовка данных
    files = {
        'image': ('test_image.png', open('test_image.png', 'rb'), 'image/png')
    }
    
    data = {
        'company_id': COMPANY_ID,
        'project_id': PROJECT_ID,
        'title': 'Test AR Content',
        'description': 'Test content for preview generation'
    }
    
    try:
        response = requests.post(url, files=files, data=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        files['image'][1].close()

if __name__ == "__main__":
    print("Testing AR Content creation...")
    result = test_create_ar_content()
    if result:
        print("Test completed successfully!")
    else:
        print("Test failed!")