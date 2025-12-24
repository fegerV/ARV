import requests
import json

# First, get the auth token
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
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get('access_token')
        print(f"Access Token: {access_token}")
        
        # Now test a protected endpoint
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Test getting current user info
        user_response = requests.get(
            "http://localhost:8000/api/auth/me",
            headers=headers
        )
        
        print(f"User Info Status: {user_response.status_code}")
        print(f"User Info: {user_response.text}")
        
        # Test health endpoint
        health_response = requests.get(
            "http://localhost:8000/api/health/status",
            headers=headers
        )
        
        print(f"Health Status: {health_response.status_code}")
        print(f"Health Info: {health_response.text}")
        
    else:
        print(f"Login failed with status {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")