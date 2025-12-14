import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.company import Company

@pytest.fixture(scope="function")
async def debug_test_session():
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
        print(f"Session type inside context: {type(session)}")
        print(f"Session has add: {hasattr(session, 'add')}")
        yield session

@pytest.mark.asyncio
async def test_debug_session(debug_test_session):
    """Debug test to see session type."""
    print(f"Session type received: {type(debug_test_session)}")
    print(f"Session has add: {hasattr(debug_test_session, 'add')}")
    
    if hasattr(debug_test_session, '__anext__'):
        print("Session is async generator")
        # Try to get actual session
        actual_session = await debug_test_session.__anext__()
        print(f"Actual session type: {type(actual_session)}")
        print(f"Actual session has add: {hasattr(actual_session, 'add')}")
    else:
        print("Session is not async generator")