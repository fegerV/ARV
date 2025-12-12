"""
Test configuration and fixtures for Vertex AR platform tests.
"""

import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.core.database import Base, get_db
from app.core.config import get_settings
from app.models import user, company, storage, ar_content  # Import all models


@pytest.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    test_database_url = "sqlite+aiosqlite:///:memory:"
    
    test_engine = create_async_engine(
        test_database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    await test_engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine):
    """Create a test database session."""
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    # Seed data
    await seed_test_data(TestSessionLocal)
    
    async with TestSessionLocal() as session:
        yield session


async def seed_test_data(session_factory):
    """Seed test database with default data."""
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole
    from app.models.storage import StorageConnection
    from app.models.company import Company
    
    async with session_factory() as session:
        default_admin = User(
            email="admin@vertexar.com",
            hashed_password=get_password_hash("admin123"),
            full_name="Vertex AR Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(default_admin)
        await session.flush()
        
        default_storage = StorageConnection(
            name="Test Local Storage",
            provider="local_disk",
            base_path="/tmp/test_storage",
            is_active=True,
            is_default=True,
            credentials={},
        )
        session.add(default_storage)
        await session.flush()
        
        default_company = Company(
            name="Vertex AR",
            slug="vertex-ar",
            storage_connection_id=default_storage.id,
            storage_path="/",
            is_default=True,
            is_active=True,
            notes="Default test company.",
        )
        session.add(default_company)
        
        await session.commit()


@pytest.fixture(scope="function")
async def async_client(test_session):
    """Create a test client."""
    async def override_get_db():
        yield test_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def admin_token(async_client):
    """Get admin auth token."""
    login_data = {
        "username": "admin@vertexar.com",
        "password": "admin123"
    }
    
    response = await async_client.post("/api/auth/login", data=login_data)
    assert response.status_code == 200
    
    return response.json()["access_token"]


@pytest.fixture(scope="function")
async def auth_client(async_client, admin_token):
    """Create authenticated client."""
    async_client.headers["Authorization"] = f"Bearer {admin_token}"
    yield async_client
    del async_client.headers["Authorization"]