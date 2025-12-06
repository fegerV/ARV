import requests
import json

# Make a POST request to the login endpoint
response = requests.post(
    "http://localhost:8000/api/auth/login",
    data={
        "username": "admin@vertexar.com",
        "password": "pass123"
    },
    headers={
        "accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")

# If successful, parse and display the token
if response.status_code == 200:
    data = response.json()
    print(f"Access Token: {data.get('access_token')}")
    print(f"User: {data.get('user', {}).get('name')}")
    print(f"Role: {data.get('user', {}).get('role')}")