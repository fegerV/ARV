import requests
import time

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
        'title': 'Test AR Content for Preview',
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

def test_get_ar_content(content_id):
    """Тест получения AR контента"""
    url = f"{BASE_URL}/api/ar-content/{content_id}"
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("Testing AR Content creation with preview generation...")
    result = test_create_ar_content()
    
    if result and 'id' in result:
        content_id = result['id']
        print(f"Created content with ID: {content_id}")
        
        # Ждем немного, чтобы задача генерации превью успела выполниться
        print("Waiting for preview generation...")
        time.sleep(10)
        
        # Проверяем, создались ли превью
        print("Checking content details...")
        test_get_ar_content(content_id)
    else:
        print("Failed to create content!")