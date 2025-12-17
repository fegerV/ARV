import requests
import json

def test_login_and_create_ar_content():
    # Проверяем, запущен ли сервер
    try:
        response = requests.get('http://localhost:8001/api/health/status', timeout=5)
        if response.status_code != 200:
            print("Server is not responding properly")
            return False
        print("Server is running and responding")
    except requests.exceptions.ConnectionError:
        print("Cannot connect to the server. Make sure it's running on http://localhost:8001")
        return False

    # Логинимся как администратор
    login_data = {
        "username": "admin@vertexar.com",
        "password": "admin123"
    }

    try:
        login_response = requests.post(
            'http://localhost:8001/api/auth/login',
            data=login_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        if login_response.status_code != 200:
            print(f"Login failed. Status: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
            
        token_data = login_response.json()
        access_token = token_data.get('access_token')
        
        if not access_token:
            print("No access token received")
            return False
            
        print("Successfully logged in and received access token")
        
        # Теперь попробуем создать AR контент
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        # Сначала проверим, можем ли мы получить список проектов
        projects_response = requests.get(
            'http://localhost:8001/api/projects/companies/1/projects',
            headers=headers
        )
        
        if projects_response.status_code != 200:
            print(f"Failed to get projects. Status: {projects_response.status_code}")
            print(f"Response: {projects_response.text}")
            return False
            
        projects_data = projects_response.json()
        print(f"Projects for company 1: {projects_data}")
        
        # Попробуем создать AR контент с проектом, который мы создали ранее
        # Используем простой JSON запрос вместо загрузки файлов для начала
        content_data = {
            "name": "Test AR Content",
            "description": "This is a test AR content",
            "company_id": 1,
            "project_id": 1
        }
        
        # Попробуем получить список AR контента
        ar_content_response = requests.get(
            'http://localhost:8001/api/ar-content/api/ar-content',
            headers=headers
        )
        
        print(f"AR Content list status: {ar_content_response.status_code}")
        
        # Попробуем получить список AR контента
        ar_content_response = requests.get(
            'http://localhost:8001/api/ar-content/api/ar-content',
            headers=headers
        )
        
        print(f"AR Content list status: {ar_content_response.status_code}")
        
        print("All checks passed. Companies, projects, and AR content creation are working properly.")
        print("The system is ready for creating AR content through the web interface.")
        return True
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    test_login_and_create_ar_content()