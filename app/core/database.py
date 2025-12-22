"""Database configuration and session management."""

import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Disable connection pooling for development
    echo=settings.DEBUG,
    connect_args={
        "server_settings": {
            "application_name": "vertex_ar_api"
        }
    }
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


def init_db_sync() -> None:
    """Initialize database by running Alembic migrations"""
    from alembic.config import Config
    from alembic import command
    import os
    from pathlib import Path
    
    try:
        # Create alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Set the script location to the alembic directory
        alembic_cfg.set_main_option("script_location", "alembic")
        
        # Set the database URL
        from app.core.config import settings
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        # Run migrations to upgrade to the latest version
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations applied successfully")
    except Exception as e:
        logger.error(f"Error applying database migrations: {e}")
        # Don't raise the exception to allow the application to start
        # The database might be initialized later or manually
        import traceback
        traceback.print_exc()


async def init_db() -> None:
    """Initialize database - but skip migrations since they're handled separately"""
    logger.info("Database initialized (migrations handled separately)")


async def seed_defaults() -> None:
    """Seed default storage connection and company if missing."""
    from sqlalchemy import select
    from app.models.storage import StorageConnection
    from app.models.company import Company
    from app.models.user import User
    from app.core.security import get_password_hash
    from app.enums import CompanyStatus
    from pathlib import Path
    
    async with AsyncSessionLocal() as session:
        # Default admin user
        res_user = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin_user = res_user.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                full_name="Vertex AR Admin",
                role="admin",  # Простая строка вместо ENUM
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()

        # Default local storage connection
        res_storage = await session.execute(select(StorageConnection))
        default_storage = res_storage.scalar_one_or_none()
        if not default_storage:
            storage_path = Path("/app/storage/content")
            storage_path.mkdir(parents=True, exist_ok=True)
            
            default_storage = StorageConnection(
                name="Local Storage",
                provider="local_disk",
                base_path=str(storage_path),
                is_active=True,
                is_default=True,
            )
            session.add(default_storage)
            await session.flush()
            
            logger.info("local_storage_structure_created", base_path=str(storage_path))

        # Default company
        res_company = await session.execute(select(Company))
        default_company = res_company.scalar_one_or_none()
        if not default_company:
            default_company = Company(
                name="Vertex AR",
                slug="vertex-ar",  # Добавляем slug
                contact_email=settings.ADMIN_EMAIL,
                status=CompanyStatus.ACTIVE
            )
            session.add(default_company)
            await session.flush()
            
            logger.info("default_company_created", company_id=default_company.id)

        await session.commit()
        logger.info("defaults_seeded")