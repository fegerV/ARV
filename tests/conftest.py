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
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus


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
        
        # Create a simple test company with current model structure
        default_company = Company(
            name="Vertex AR",
            contact_email="admin@vertexar.com",
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


# Model factories for unit tests
@pytest.fixture(scope="function")
def company_factory():
    """Factory to create test companies."""
    async def _create_company(session: AsyncSession, name: str = None, contact_email: str = None, status: str = None) -> Company:
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        company = Company(
            name=name or f"Test Company {unique_id}",
            contact_email=contact_email or f"test{unique_id}@example.com",
            status=status or CompanyStatus.ACTIVE
        )
        session.add(company)
        await session.flush()
        return company
    return _create_company


@pytest.fixture(scope="function") 
def project_factory():
    """Factory to create test projects."""
    async def _create_project(session: AsyncSession, name: str = None, company_id: str = None, status: str = None) -> Project:
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        if company_id is None:
            company = await _create_company(session)
            company_id = company.id
            
        project = Project(
            name=name or f"Test Project {unique_id}",
            company_id=company_id,
            status=status or ProjectStatus.ACTIVE
        )
        session.add(project)
        await session.flush()
        return project
    return _create_project


@pytest.fixture(scope="function")
def ar_content_factory():
    """Factory to create test AR content."""
    async def _create_ar_content(
        session: AsyncSession,
        order_number: str = None, 
        project_id: str = None,
        customer_name: str = None,
        status: str = None
    ) -> ARContent:
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        if project_id is None:
            project = await _create_project(session)
            project_id = project.id
            
        ar_content = ARContent(
            project_id=project_id,
            order_number=order_number or f"ORDER-{unique_id}",
            customer_name=customer_name or f"Test Customer {unique_id}",
            status=status or ArContentStatus.PENDING
        )
        session.add(ar_content)
        await session.flush()
        return ar_content
    return _create_ar_content


@pytest.fixture(scope="function")
def video_factory():
    """Factory to create test videos."""
    async def _create_video(
        session: AsyncSession,
        ar_content_id: str = None,
        filename: str = None,
        video_status: str = None
    ) -> Video:
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        if ar_content_id is None:
            ar_content = await _create_ar_content(session)
            ar_content_id = ar_content.id
            
        video = Video(
            ar_content_id=ar_content_id,
            filename=filename or f"test_video_{unique_id}.mp4",
            video_status=video_status or VideoStatus.UPLOADED
        )
        session.add(video)
        await session.flush()
        return video
    return _create_video