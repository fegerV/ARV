import requests
import time

try:
    # Ждем немного, чтобы сервер успел запуститься
    time.sleep(2)
    
    # Проверяем доступность сервера
    response = requests.get('http://localhost:8000/api/health/status', timeout=5)
    print(f"Статус ответа: {response.status_code}")
    print(f"Тело ответа: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Ошибка при подключении к серверу: {e}")
except Exception as e:
    print(f"Неизвестная ошибка: {e}")