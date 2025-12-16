import requests
import json

# Test login
login_data = {
    "username": "admin@vertexar.com",
    "password": "admin123"
}

try:
    response = requests.post(
        "http://localhost:8000/api/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        token_data = response.json()
        print(f"Access Token: {token_data.get('access_token')}")
        print(f"Token Type: {token_data.get('token_type')}")
    else:
        print("Login failed")
        
except Exception as e:
    print(f"Error: {e}")