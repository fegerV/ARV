from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database (create tables if not exist)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_defaults() -> None:
    """Seed default storage connection and company if missing."""
    from sqlalchemy import select
    from app.models.storage import StorageConnection
    from app.models.company import Company
    from pathlib import Path
    
    async with AsyncSessionLocal() as session:
        # Default local storage connection
        res = await session.execute(select(StorageConnection).where(StorageConnection.is_default == True))
        default_conn = res.scalar_one_or_none()
        if not default_conn:
            default_conn = StorageConnection(
                name="Vertex AR Local Storage",
                provider="local_disk",
                base_path=settings.LOCAL_STORAGE_PATH,
                is_active=True,
                is_default=True,
                credentials={},
            )
            session.add(default_conn)
            await session.flush()

        # Default company
        res2 = await session.execute(select(Company).where(Company.slug == "vertex-ar"))
        default_company = res2.scalar_one_or_none()
        if not default_company:
            default_company = Company(
                name="Vertex AR",
                slug="vertex-ar",
                storage_connection_id=default_conn.id,
                storage_path="/",
                is_default=True,
                is_active=True,
                notes="Default Vertex AR company with local storage.",
            )
            session.add(default_company)

        # Create base folder structure for local storage
        try:
            base_dir = Path(settings.LOCAL_STORAGE_PATH)
            for sub in ["ar-content", "videos", "markers", "qr-codes", "thumbnails"]:
                (base_dir / sub).mkdir(parents=True, exist_ok=True)
            
            # Create company structure
            companies_dir = base_dir / "companies"
            companies_dir.mkdir(parents=True, exist_ok=True)
            
            logger = __import__('structlog').get_logger()
            logger.info("local_storage_structure_created", base_path=str(base_dir))
        except Exception as e:
            logger = __import__('structlog').get_logger()
            logger.warning("failed_to_create_storage_structure", error=str(e))

        await session.commit()
async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
