import requests
import time

def test_api():
    """Test if the API is responding"""
    try:
        start_time = time.time()
        response = requests.get('http://localhost:8000/api/health/status', timeout=10)
        end_time = time.time()
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {end_time - start_time:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Data: {data}")
        else:
            print(f"Error response: {response.text}")
    except requests.exceptions.ConnectionError as e:
        print(f"Error connecting to API: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout connecting to API: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_api()