import requests

# URL API
url = "http://localhost:8000/api/ar-content"

# Данные формы для компании по умолчанию
data = {
    "company_id": "1",  # ID компании Vertex AR
    "project_id": "2",  # ID проекта, который мы только что создали
    "title": "Default Company AR Content",
    "description": "Test AR content using default company",
    "client_name": "Default Client",
    "client_email": "default@test.com",
    "client_phone": "+1234567890"
}

# Файлы для загрузки (используем те же тестовые файлы)
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
    
    # Проверяем успешность создания
    if response.status_code == 200:
        print("AR content successfully created with default company!")
    else:
        print("Failed to create AR content with default company")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    # Закрываем файлы
    for file_tuple in files.values():
        file_tuple[1].close()