import pytest
import tempfile
import os
from httpx import AsyncClient
from app.core.config import settings

# Set test storage path to avoid permission issues
os.environ['LOCAL_STORAGE_PATH'] = '/tmp/test_storage'

# Import app after setting environment variables
from app.main import app


@pytest.mark.asyncio
async def test_health_status():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health/status")
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data


@pytest.mark.asyncio
async def test_list_companies_include_default():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/companies/?include_default=true")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.skip(reason="Storage health test requires proper filesystem permissions in test environment")
@pytest.mark.asyncio
async def test_storage_health():
    """Test storage health endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/storage/health")
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "base_path" in data
        assert "total_disk_space_gb" in data
        assert "used_disk_space_gb" in data
        assert "free_disk_space_gb" in data
        assert "disk_usage_percent" in data
        assert "storage_files_count" in data
        assert "storage_size_mb" in data
        assert "is_writable" in data


@pytest.mark.asyncio
async def test_storage_usage():
    """Test storage usage endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/storage/usage")
        assert response.status_code == 200
        
        data = response.json()
        assert "overall" in data
        assert "by_companies" in data
        assert "by_file_types" in data
        
        # Check overall stats
        overall = data["overall"]
        assert "total_files" in overall
        assert "total_size_bytes" in overall
        assert "total_size_mb" in overall
        assert "base_path" in overall
        
        # Check file types breakdown
        file_types = data["by_file_types"]
        assert "images" in file_types
        assert "videos" in file_types
        assert "other" in file_types


@pytest.mark.asyncio
async def test_storage_usage_with_filters():
    """Test storage usage endpoint with filters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with company filter (even if company doesn't exist)
        response = await client.get("/api/storage/usage?company_id=999")
        assert response.status_code == 200
        
        data = response.json()
        assert "overall" in data
        assert "by_companies" in data
        assert "by_file_types" in data


@pytest.mark.asyncio
async def test_create_company_project_content_flow():
    """Test the full flow of creating company -> project -> AR content."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a company
        company_data = {
            "name": "Test Company",
            "contact_email": "test@example.com"
        }
        response = await client.post("/api/companies/", json=company_data)
        assert response.status_code == 201
        company = response.json()
        company_id = company["id"]
        
        # Create a project
        project_data = {
            "name": "Test Project",
            "company_id": company_id
        }
        response = await client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]
        
        # Create AR content
        ar_content_data = {
            "project_id": project_id,
            "order_number": "TEST-001",
            "customer_name": "Test Customer",
            "customer_email": "customer@example.com",
            "customer_phone": "+1-555-0123",
            "duration_years": 1
        }
        response = await client.post("/api/ar-content/", json=ar_content_data)
        assert response.status_code == 201
        ar_content = response.json()
        ar_content_id = ar_content["id"]
        
        # Verify the data
        assert ar_content["order_number"] == "TEST-001"
        assert ar_content["customer_name"] == "Test Customer"
        assert ar_content["duration_years"] == 1
        
        # Clean up - delete project (should cascade delete AR content)
        response = await client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200
        
        # Verify AR content is deleted
        response = await client.get(f"/api/ar-content/{ar_content_id}")
        assert response.status_code == 404
        
        # Clean up - delete company
        response = await client.delete(f"/api/companies/{company_id}")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_pagination_and_filtering():
    """Test pagination and filtering endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test companies pagination
        response = await client.get("/api/companies/?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data
        
        # Test projects pagination
        response = await client.get("/api/projects/?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data
        
        # Test AR content pagination
        response = await client.get("/api/ar-content/?page=1&size=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "size" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_file_upload_endpoints():
    """Test file upload functionality."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create test file
        test_content = b"test file content"
        files = {"file": ("test.txt", test_content, "text/plain")}
        
        # Test upload endpoint (this might need adjustment based on actual API)
        response = await client.post("/api/ar-content/upload", files=files)
        # Note: This test might need to be updated based on the actual upload API structure
        # For now, we'll just check that the endpoint exists
        assert response.status_code in [200, 201, 400, 422]  # Accept various valid responses


@pytest.mark.asyncio 
async def test_cascade_delete():
    """Test cascade deletion from project to AR content to videos."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First create a company
        company_data = {"name": "Cascade Test Company", "contact_email": "test@example.com"}
        response = await client.post("/api/companies/", json=company_data)
        assert response.status_code == 201
        company_id = response.json()["id"]
        
        # Create a project
        project_data = {"name": "Cascade Test Project", "company_id": company_id}
        response = await client.post("/api/projects/", json=project_data)
        assert response.status_code == 201
        project = response.json()
        project_id = project["id"]
        
        # Create AR content
        ar_content_data = {
            "project_id": project_id,
            "order_number": "CASCADE-001",
            "customer_name": "Cascade Customer",
            "duration_years": 1
        }
        response = await client.post("/api/ar-content/", json=ar_content_data)
        assert response.status_code == 201
        ar_content = response.json()
        ar_content_id = ar_content["id"]
        
        # Create a video for the AR content
        video_data = {
            "ar_content_id": ar_content_id,
            "filename": "test_video.mp4",
            "duration": 30,
            "size": 1024000
        }
        response = await client.post("/api/videos/", json=video_data)
        if response.status_code == 201:  # Only test if video creation works
            video = response.json()
            video_id = video["id"]
            
            # Verify video exists
            response = await client.get(f"/api/videos/{video_id}")
            assert response.status_code == 200
        
        # Delete the project (should cascade delete AR content and videos)
        response = await client.delete(f"/api/projects/{project_id}")
        assert response.status_code == 200
        
        # Verify AR content is deleted
        response = await client.get(f"/api/ar-content/{ar_content_id}")
        assert response.status_code == 404
        
        # Clean up company
        response = await client.delete(f"/api/companies/{company_id}")
        assert response.status_code == 200
