import requests
import os
import sys
from pathlib import Path

# Добавляем путь к проекту, чтобы можно было импортировать модули
sys.path.insert(0, str(Path(__file__).parent))

def test_ar_content_creation():
    # Проверяем, запущен ли сервер
    try:
        response = requests.get('http://localhost:8000/api/health', timeout=5)
        if response.status_code != 200:
            print("Server is not responding properly")
            return False
        print("Server is running and responding")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to the server. Make sure it's running on http://localhost:8000")
        return False

    # Получаем токен аутентификации (предполагаем, что есть тестовый пользователь)
    # В реальной ситуации нужно будет использовать логин/пароль или получить токен другим способом
    auth_token = os.getenv('AUTH_TOKEN')
    
    if not auth_token:
        print("No authentication token found. Please set AUTH_TOKEN environment variable with a valid JWT token.")
        print("You may need to log in first through the web interface to get a valid token.")
        return False

    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Accept': 'application/json'
    }

    # Подготовим тестовые данные для создания AR контента
    # Сначала создадим тестовое изображение
    import io
    from PIL import Image
    
    # Создаем простое тестовое изображение
    img = Image.new('RGB', (300, 300), color='red')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_io.seek(0)
    
    # Подготовим данные для отправки
    files = {
        'image': ('test_image.jpg', img_io, 'image/jpeg'),
    }
    
    data = {
        'name': 'Test AR Content',
        'description': 'This is a test AR content created via API',
        'content_metadata': '{"customer_name": "Test Customer", "customer_email": "test@example.com", "schedule_type": "daily", "schedule_time": "09:00", "playback_duration": "3_years"}'
    }

    try:
        # Отправляем запрос на создание AR контента
        # Используем компанию ID 1 и проект ID 1, которые мы создали ранее
        response = requests.post(
            'http://localhost:8000/api/ar-content/companies/1/projects/1/ar-content/new',
            files=files,
            data=data,
            headers=headers,
            timeout=30
        )
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code == 200:
            print("AR content created successfully!")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Failed to create AR content. Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error during AR content creation: {str(e)}")
        return False

if __name__ == "__main__":
    test_ar_content_creation()