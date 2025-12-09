import requests

# URL API
url = "http://localhost:8000/api/ar-content"

# Данные формы
data = {
    "company_id": "2",
    "project_id": "1",
    "title": "Test AR Content",
    "description": "Test AR content for testing purposes",
    "client_name": "Test Client",
    "client_email": "client@test.com",
    "client_phone": "+1234567890"
}

# Файлы для загрузки
files = {
    "image": ("test_image.jpg", open("test_image.jpg", "rb"), "image/jpeg"),
    "videos": ("test_video.mp4", open("test_video.mp4", "rb"), "video/mp4")
}

try:
    # Отправляем POST запрос
    response = requests.post(url, data=data, files=files)
    
    # Выводим результат
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    # Закрываем файлы
    for file_tuple in files.values():
        file_tuple[1].close()