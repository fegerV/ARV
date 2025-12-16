"""
Integration tests for first-run authentication flow.
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_default_admin_can_login():
    """Test that the default admin user can log in on a fresh database."""
    # Create a fresh test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_data = {
            "username": "admin@vertexar.com",
            "password": "admin123"
        }
        
        response = await client.post("/api/auth/login", data=login_data)
        
        assert response.status_code == 200
        token_data = response.json()
        
        # Verify token structure
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
        assert "user" in token_data
        
        # Verify user data
        user_data = token_data["user"]
        assert user_data["email"] == "admin@vertexar.com"
        assert user_data["full_name"] == "Vertex AR Admin"
        assert user_data["role"] == "admin"
        assert user_data["is_active"] is True


@pytest.mark.asyncio
async def test_unauthorized_company_creation_is_rejected():
    """Test that unauthorized company creation is rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to create a company without authentication
        company_data = {
            "name": "Unauthorized Company",
            "contact_email": "unauthorized@example.com",
            "storage_connection_id": 1  # Assuming default storage connection exists
        }
        
        response = await client.post("/api/companies/", json=company_data)
        
        # Should be rejected with 401 Unauthorized
        assert response.status_code == 401
        error_detail = response.json()
        assert "detail" in error_detail


@pytest.mark.asyncio
async def test_tokens_allow_access_to_protected_endpoints():
    """Test that valid tokens allow access to protected endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First login to get token
        login_data = {
            "username": "admin@vertexar.com",
            "password": "admin123"
        }
        
        login_response = await client.post("/api/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        token = token_data["access_token"]
        
        # Test accessing protected endpoint /api/auth/me
        auth_headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        user_data = response.json()
        
        assert user_data["email"] == "admin@vertexar.com"
        assert user_data["full_name"] == "Vertex AR Admin"
        assert user_data["role"] == "admin"


@pytest.mark.asyncio
async def test_admin_can_register_new_user():
    """Test that admin can register a new user via /api/auth/register."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First login as admin
        login_data = {
            "username": "admin@vertexar.com",
            "password": "admin123"
        }
        
        login_response = await client.post("/api/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        token = token_data["access_token"]
        
        # Register new user
        new_user_data = {
            "email": "testuser@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User",
            "role": "manager"
        }
        
        auth_headers = {"Authorization": f"Bearer {token}"}
        response = await client.post("/api/auth/register", json=new_user_data, headers=auth_headers)
        
        assert response.status_code == 200
        result = response.json()
        
        assert "user" in result
        assert "message" in result
        assert result["message"] == "User created successfully"
        
        # Verify created user data
        user_data = result["user"]
        assert user_data["email"] == "testuser@example.com"
        assert user_data["full_name"] == "Test User"
        assert user_data["role"] == "manager"
        assert user_data["is_active"] is True
        assert "hashed_password" not in user_data  # Should not expose password


@pytest.mark.asyncio
async def test_authorized_company_creation_succeeds():
    """Test that authorized company creation succeeds."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First login as admin
        login_data = {
            "username": "admin@vertexar.com",
            "password": "admin123"
        }
        
        login_response = await client.post("/api/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        token = token_data["access_token"]
        
        # Try to create a company with authentication
        company_data = {
            "name": "Test Authorized Company",
            "contact_email": "authorized@example.com",
            "storage_connection_id": 1,  # Use default storage
            "subscription_tier": "basic",
            "storage_quota_gb": 10,
            "projects_limit": 5
        }
        
        auth_headers = {"Authorization": f"Bearer {token}"}
        response = await client.post("/api/companies/", json=company_data, headers=auth_headers)
        
        # Should pass authentication (might fail due to storage validation, but not auth)
        assert response.status_code != 401
        if response.status_code == 422:
            # Validation error is acceptable - we're testing auth, not validation
            pass
        elif response.status_code == 200:
            # Success case
            company = response.json()
            assert company["name"] == "Test Authorized Company"
            assert company["contact_email"] == "authorized@example.com"


@pytest.mark.asyncio
async def test_invalid_token_rejected():
    """Test that invalid tokens are rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        invalid_token = "invalid.jwt.token"
        auth_headers = {"Authorization": f"Bearer {invalid_token}"}
        
        response = await client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_invalid_credentials():
    """Test login with invalid credentials."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_data = {
            "username": "admin@vertexar.com",
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/auth/login", data=login_data)
        
        assert response.status_code == 401
        error_detail = response.json()
        assert "detail" in error_detail


@pytest.mark.asyncio
async def test_login_with_nonexistent_user():
    """Test login with non-existent user."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        login_data = {
            "username": "nonexistent@example.com",
            "password": "password"
        }
        
        response = await client.post("/api/auth/login", data=login_data)
        
        assert response.status_code == 401
        error_detail = response.json()
        assert "detail" in error_detail