"""Database configuration and session management."""

import asyncio
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import OperationalError
from typing import AsyncGenerator
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Retry config for SQLite "database is locked" during reload
SEED_DEFAULTS_RETRY_COUNT = 3
SEED_DEFAULTS_RETRY_DELAY_SEC = 0.4

def _is_sqlite_url(database_url: str) -> bool:
    """Return True if the database URL points to SQLite."""
    return database_url.startswith("sqlite")


def _build_engine():
    """Create async SQLAlchemy engine with safe defaults."""
    if settings.DEBUG or not settings.is_production or _is_sqlite_url(settings.DATABASE_URL):
        pool_options = {"poolclass": NullPool}
    else:
        pool_options = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_pre_ping": True,
            "pool_recycle": 1800,   # recycle stale connections every 30 min
            "pool_timeout": 30,     # fail fast if pool exhausted (seconds)
        }

    return create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        connect_args={},
        **pool_options,
    )


# Create async engine with connection pooling
engine = _build_engine()

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Naming convention for constraints — ensures deterministic names for Alembic
# migrations (especially critical for downgrade operations).
_naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Base class for SQLAlchemy models
Base = declarative_base(metadata=MetaData(naming_convention=_naming_convention))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get async database session.

    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            logger.exception("database_session_failed")
            await session.rollback()
            raise
        # Явный session.close() не вызываем: при выходе из async with
        # сессия закрывается контекстным менеджером; иначе возможен
        # IllegalStateChangeError при одновременном _connection_for_bind().


def init_db_sync() -> None:
    """Initialize database by running Alembic migrations"""
    from alembic.config import Config
    from alembic import command

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


def _is_sqlite_locked_error(exc: OperationalError) -> bool:
    """True if error is SQLite 'database is locked' / 'database is busy'."""
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


async def seed_defaults() -> None:
    """Seed default storage connection and company if missing.
    Retries on SQLite 'database is locked' (e.g. during uvicorn --reload).
    """
    from sqlalchemy import select, func
    from app.models.storage import StorageConnection
    from app.models.company import Company
    from app.models.user import User
    from app.core.security import get_password_hash
    from app.enums import CompanyStatus
    from pathlib import Path

    for attempt in range(SEED_DEFAULTS_RETRY_COUNT):
        try:
            async with AsyncSessionLocal() as session:
                # Default admin user
                res_user = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
                admin_user = res_user.scalar_one_or_none()
                if not admin_user:
                    admin_user = User(
                        email=settings.ADMIN_EMAIL,
                        hashed_password=get_password_hash(settings.ADMIN_DEFAULT_PASSWORD),
                        full_name="Vertex AR Admin",
                        role="admin",
                        is_active=True,
                    )
                    session.add(admin_user)
                    await session.flush()
                else:
                    admin_user.hashed_password = get_password_hash(settings.ADMIN_DEFAULT_PASSWORD)
                    logger.info("default_admin_exists", user_id=admin_user.id)

                # Default local storage connection
                res_storage = await session.execute(select(StorageConnection).where(StorageConnection.name == "Local Storage"))
                default_storage = res_storage.scalar_one_or_none()
                if not default_storage:
                    storage_path = Path(settings.STORAGE_BASE_PATH)
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
                DEFAULT_COMPANY_NAMES = ["Vertex AR", "VertexAR", "vertex-ar", "vertexar"]
                res_company = await session.execute(
                    select(Company).where(
                        (func.lower(Company.name).in_([n.lower() for n in DEFAULT_COMPANY_NAMES]))
                        | (Company.slug == "vertex-ar")
                    )
                )
                default_company = res_company.scalar_one_or_none()
                if not default_company:
                    default_company = Company(
                        name="Vertex AR",
                        slug="vertex-ar",
                        contact_email=settings.ADMIN_EMAIL,
                        status=CompanyStatus.ACTIVE,
                    )
                    session.add(default_company)
                    await session.flush()
                    logger.info("default_company_created", company_id=default_company.id)
                else:
                    default_company.name = "Vertex AR"
                    default_company.slug = "vertex-ar"
                    default_company.contact_email = settings.ADMIN_EMAIL
                    default_company.status = CompanyStatus.ACTIVE
                    logger.info("default_company_updated", company_id=default_company.id)

                await session.commit()
                logger.info("defaults_seeded")
            return
        except OperationalError as e:
            if _is_sqlite_locked_error(e) and attempt < SEED_DEFAULTS_RETRY_COUNT - 1:
                logger.debug("seed_defaults_retry", attempt=attempt + 1, error=str(e))
                await asyncio.sleep(SEED_DEFAULTS_RETRY_DELAY_SEC)
            else:
                raise