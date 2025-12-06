import requests

# First, login to get the access token
login_response = requests.post(
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

if login_response.status_code == 200:
    data = login_response.json()
    access_token = data.get('access_token')
    print(f"Successfully logged in!")
    print(f"Access Token: {access_token}")
    
    # Now use the token to access a protected endpoint
    headers = {
        "Authorization": f"Bearer {access_token}",
        "accept": "application/json"
    }
    
    # Try to access the current user info
    user_response = requests.get(
        "http://localhost:8000/api/auth/me",
        headers=headers
    )
    
    print(f"\nUser Info Status Code: {user_response.status_code}")
    if user_response.status_code == 200:
        user_data = user_response.json()
        print(f"User Info: {user_data}")
        print(f"Welcome, {user_data.get('fullname')}!")
    else:
        print(f"Failed to get user info: {user_response.text}")
else:
    print(f"Login failed: {login_response.text}")