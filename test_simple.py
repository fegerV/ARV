import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.company import Company

@pytest.fixture(scope="function")
async def simple_test_session():
    """Create a simple test database session."""
    test_database_url = "sqlite+aiosqlite:///:memory:"
    
    test_engine = create_async_engine(
        test_database_url,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with TestSessionLocal() as session:
        yield session

@pytest.mark.asyncio
async def test_simple_company_creation(simple_test_session):
    """Simple test to verify session works."""
    company = Company(name="Test Company", contact_email="test@example.com")
    simple_test_session.add(company)
    await simple_test_session.flush()
    await simple_test_session.commit()
    
    assert company.id is not None
    assert company.name == "Test Company"