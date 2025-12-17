# Vertex AR B2B Platform - API Examples

## Overview

This document provides practical examples of how to integrate with the Vertex AR B2B Platform API. The examples cover common use cases and implementation patterns for different programming languages.

## Authentication Examples

### Python Example
```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000/api"

# Login
def login(email, password):
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": email,
        "password": password
    }
    
    response = requests.post(url, data=payload)
    
    if response.status_code == 200:
        data = response.json()
        token = data["access_token"]
        print(f"Login successful. Token: {token[:20]}...")
        return token
    else:
        print(f"Login failed: {response.status_code}")
        print(response.json())
        return None

# Example usage
token = login("admin@example.com", "password123")

if token:
    # Use the token for authenticated requests
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get current user info
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if response.status_code == 200:
        user_info = response.json()
        print(f"Current user: {user_info['full_name']} ({user_info['email']})")
```

### JavaScript/Node.js Example
```javascript
// Using fetch API
async function login(email, password) {
    const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`
    });

    if (response.ok) {
        const data = await response.json();
        console.log('Login successful. Token:', data.access_token.substring(0, 20) + '...');
        return data.access_token;
    } else {
        const error = await response.json();
        console.error('Login failed:', error);
        return null;
    }
}

// Example usage
login('admin@example.com', 'password123')
    .then(token => {
        if (token) {
            // Use the token for authenticated requests
            fetch('http://localhost:8000/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(user => console.log('Current user:', user.full_name));
        }
    });
```

### cURL Example
```bash
# Login and get token
TOKEN=$(curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=password123" \
  | jq -r '.access_token')

echo "Token: $TOKEN"

# Use token for authenticated requests
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

## Company Management Examples

### Creating a Company (Python)
```python
import requests

def create_company(token, name, contact_email):
    url = "http://localhost:8000/api/companies"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "contact_email": contact_email
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        company = response.json()
        print(f"Company created: {company['name']} (ID: {company['id']})")
        return company
    else:
        print(f"Failed to create company: {response.status_code}")
        print(response.json())
        return None

# Example usage
if token:
    new_company = create_company(token, "Example Corp", "contact@example.com")
```

### Listing Companies (JavaScript)
```javascript
async function listCompanies(token) {
    const response = await fetch('http://localhost:8000/api/companies', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });

    if (response.ok) {
        const data = await response.json();
        console.log('Companies:', data.items);
        return data.items;
    } else {
        console.error('Failed to list companies:', response.status);
        return [];
    }
}

// Example usage
if (token) {
    listCompanies(token).then(companies => {
        console.log(`${companies.length} companies found`);
    });
}
```

## Project Management Examples

### Creating a Project (Python)
```python
def create_project(token, company_id, name):
    url = f"http://localhost:8000/api/companies/{company_id}/projects"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        project = response.json()
        print(f"Project created: {project['name']} (ID: {project['id']})")
        return project
    else:
        print(f"Failed to create project: {response.status_code}")
        print(response.json())
        return None

# Example usage
if token and new_company:
    new_project = create_project(token, new_company['id'], "Summer Campaign")
```

## AR Content Management Examples

### Creating AR Content (Python)
```python
def create_ar_content(token, project_id, customer_name, customer_email, photo_file_path, video_file_path):
    url = "http://localhost:8000/api/ar-content"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # For multipart form data, we don't set Content-Type header (requests will set it)
    data = {
        "company_id": 1,  # You'll need to adjust this
        "project_id": project_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "duration_years": 1
    }
    
    with open(photo_file_path, 'rb') as photo_file, open(video_file_path, 'rb') as video_file:
        files = {
            'photo_file': photo_file,
            'video_file': video_file
        }
        
        response = requests.post(url, headers=headers, data=data, files=files)
        
        if response.status_code == 200:
            content = response.json()
            print(f"AR Content created: {content['order_number']}")
            print(f"Public link: {content['public_link']}")
            return content
        else:
            print(f"Failed to create AR content: {response.status_code}")
            print(response.json())
            return None

# Example usage (with sample files)
# new_content = create_ar_content(token, new_project['id'], "John Doe", "john@example.com", "sample.jpg", "sample.mp4")
```

### Getting AR Content (JavaScript)
```javascript
async function getArContent(token, contentId) {
    const response = await fetch(`http://localhost:8000/api/ar-content/${contentId}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });

    if (response.ok) {
        const content = await response.json();
        console.log('AR Content:', content);
        return content;
    } else {
        console.error('Failed to get AR content:', response.status);
        return null;
    }
}

// Example usage
// getArContent(token, 1).then(content => {
//     if (content) {
//         console.log('Content order number:', content.order_number);
//         console.log('Public link:', content.public_link);
//     }
// });
```

## Video Management Examples

### Uploading Videos (Python)
```python
def upload_videos(token, content_id, video_paths):
    url = f"http://localhost:8000/api/ar-content/{content_id}/videos"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    files = []
    for path in video_paths:
        files.append(('files', open(path, 'rb')))
    
    try:
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"Videos uploaded: {len(result['uploaded_files'])} files")
            return result
        else:
            print(f"Failed to upload videos: {response.status_code}")
            print(response.json())
            return None
    finally:
        # Close file handles
        for _, file_obj in files:
            file_obj.close()

# Example usage
# upload_result = upload_videos(token, 1, ["video1.mp4", "video2.mp4"])
```

## Analytics Examples

### Getting Company Analytics (Python)
```python
def get_company_analytics(token, company_id):
    url = f"http://localhost:8000/api/analytics/companies/{company_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        analytics = response.json()
        print(f"Company analytics for {analytics['name']}:")
        print(f"  Projects: {analytics['projects_count']}")
        print(f"  AR Content: {analytics['ar_content_count']}")
        print(f"  Total Views: {analytics['total_views']}")
        return analytics
    else:
        print(f"Failed to get analytics: {response.status_code}")
        print(response.json())
        return None

# Example usage
# if token and new_company:
#     analytics = get_company_analytics(token, new_company['id'])
```

## Error Handling Examples

### Python with Error Handling
```python
def safe_api_call(url, headers, method='GET', json_data=None, files=None):
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            if files:
                response = requests.post(url, headers=headers, files=files)
            else:
                response = requests.post(url, headers=headers, json=json_data)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=json_data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Check for rate limiting
        if response.status_code == 429:
            retry_after = response.headers.get('Retry-After', 'unknown')
            print(f"Rate limited. Retry after: {retry_after} seconds")
            return None, "RATE_LIMITED"
        
        # Check for other errors
        if not response.ok:
            error_data = response.json() if response.content else {"detail": "Unknown error"}
            print(f"API Error {response.status_code}: {error_data}")
            return None, response.status_code
        
        return response.json(), "SUCCESS"
    
    except requests.exceptions.ConnectionError:
        print("Connection error - check your network connection")
        return None, "CONNECTION_ERROR"
    except requests.exceptions.Timeout:
        print("Request timeout")
        return None, "TIMEOUT"
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None, "UNKNOWN_ERROR"

# Example usage
def create_company_safe(token, name, contact_email):
    url = "http://localhost:8000/api/companies"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "contact_email": contact_email
    }
    
    data, status = safe_api_call(url, headers, 'POST', json_data=payload)
    
    if status == "SUCCESS":
        print(f"Company created: {data['name']}")
        return data
    else:
        print(f"Failed to create company: {status}")
        return None
```

## Rate Limiting Examples

### Handling Rate Limits (JavaScript)
```javascript
async function makeApiCallWithRateLimitHandling(url, options = {}) {
    let attempts = 0;
    const maxAttempts = 3;
    
    while (attempts < maxAttempts) {
        try {
            const response = await fetch(url, options);
            
            if (response.status === 429) { // Too Many Requests
                const retryAfter = response.headers.get('X-RateLimit-Reset') || 
                                  response.headers.get('Retry-After');
                
                console.log(`Rate limited. Waiting ${retryAfter} seconds...`);
                
                // Wait for the specified time before retrying
                await new Promise(resolve => setTimeout(resolve, (parseInt(retryAfter) || 60) * 1000));
                attempts++;
                continue;
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
    
    throw new Error('Max retry attempts reached due to rate limiting');
}

// Example usage
async function getCompanyWithRateLimitHandling(token, companyId) {
    const url = `http://localhost:8000/api/companies/${companyId}`;
    const options = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    
    try {
        const company = await makeApiCallWithRateLimitHandling(url, options);
        console.log('Company:', company);
        return company;
    } catch (error) {
        console.error('Failed to get company:', error.message);
        return null;
    }
}
```

## Practical Integration Example: AR Content Workflow

Here's a complete example that demonstrates a typical workflow for creating and managing AR content:

```python
import requests
import time

class VertexARClient:
    def __init__(self, base_url, email, password):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.email = email
        self.password = password
    
    def login(self):
        """Authenticate with the API"""
        url = f"{self.base_url}/auth/login"
        payload = {
            "username": self.email,
            "password": self.password
        }
        
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            print("Authentication successful")
            return True
        else:
            print(f"Authentication failed: {response.json()}")
            return False
    
    def get_headers(self):
        """Get headers with authentication token"""
        if not self.token:
            raise Exception("Not authenticated. Call login() first.")
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def create_company(self, name, contact_email):
        """Create a new company"""
        url = f"{self.base_url}/companies"
        headers = self.get_headers()
        payload = {
            "name": name,
            "contact_email": contact_email
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create company: {response.json()}")
    
    def create_project(self, company_id, name):
        """Create a new project for a company"""
        url = f"{self.base_url}/companies/{company_id}/projects"
        headers = self.get_headers()
        payload = {
            "name": name
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to create project: {response.json()}")
    
    def create_ar_content(self, project_id, customer_name, customer_email, photo_path, video_path):
        """Create new AR content with photo and video files"""
        url = f"{self.base_url}/ar-content"
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        data = {
            "company_id": 1,  # You'll need to get this dynamically
            "project_id": project_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "duration_years": 1
        }
        
        with open(photo_path, 'rb') as photo_file, open(video_path, 'rb') as video_file:
            files = {
                'photo_file': photo_file,
                'video_file': video_file
            }
            
            response = requests.post(url, headers=headers, data=data, files=files)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to create AR content: {response.json()}")
    
    def get_ar_content(self, content_id):
        """Get AR content details"""
        url = f"{self.base_url}/ar-content/{content_id}"
        headers = self.get_headers()
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get AR content: {response.json()}")

# Example usage
def main():
    # Initialize client
    client = VertexARClient(
        base_url="http://localhost:800/api",
        email="admin@example.com",
        password="password123"
    )
    
    # Authenticate
    if not client.login():
        return
    
    try:
        # Create a company
        company = client.create_company("Example Corp", "contact@example.com")
        print(f"Created company: {company['name']} (ID: {company['id']})")
        
        # Create a project
        project = client.create_project(company['id'], "Summer Campaign")
        print(f"Created project: {project['name']} (ID: {project['id']})")
        
        # Create AR content (uncomment and provide actual file paths)
        # content = client.create_ar_content(
        #     project_id=project['id'],
        #     customer_name="John Doe",
        #     customer_email="john@example.com",
        #     photo_path="path/to/photo.jpg",
        #     video_path="path/to/video.mp4"
        # )
        # print(f"Created AR content: {content['order_number']}")
        # print(f"Public link: {content['public_link']}")
        
    except Exception as e:
        print(f"Error in workflow: {str(e)}")

if __name__ == "__main__":
    main()
```

## Best Practices

### 1. Token Management
- Store tokens securely and refresh them before they expire
- Handle token expiration gracefully by re-authenticating when receiving 401 errors

### 2. Rate Limiting
- Always check rate limit headers in API responses
- Implement exponential backoff for retry logic
- Design your application to handle rate limiting gracefully

### 3. Error Handling
- Implement comprehensive error handling for different HTTP status codes
- Log errors appropriately for debugging
- Provide meaningful error messages to users

### 4. File Uploads
- Validate file types and sizes before upload
- Implement progress indicators for large file uploads
- Handle upload failures and implement retry logic

### 5. Security
- Never expose API tokens in client-side code
- Use HTTPS for all API calls in production
- Sanitize all input data to prevent injection attacks

## Troubleshooting

### Common Issues and Solutions

1. **401 Unauthorized Errors**
   - Ensure your token is valid and not expired
   - Check that the Authorization header is properly formatted

2. **429 Rate Limit Errors**
   - Check rate limit headers to understand when you can make the next request
   - Implement retry logic with exponential backoff

3. **42 Validation Errors**
   - Verify that all required fields are provided
   - Check that data types and formats are correct

4. **File Upload Issues**
   - Verify file size limits
   - Ensure supported file formats
   - Check file permissions and paths

### Debugging Tips

- Enable detailed logging to track API requests and responses
- Use API testing tools like Postman or Insomnia for manual testing
- Check server logs for detailed error information
- Monitor rate limit headers to optimize your API usage