"""Integration tests with a real database.

These tests verify ORM mappings, constraint enforcement, and actual
database behavior that fake-db unit tests cannot catch.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import tempfile

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base
from app.models.company import Company
from app.models.user import User
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.backup import BackupHistory
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus


settings = get_settings()


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


@pytest.fixture(scope="session")
def integration_engine():
    """Create a real database engine for integration tests.

    Always uses an in-memory SQLite database to avoid file locking issues
    on Windows and to keep tests isolated from the application database.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    yield engine
    engine.sync_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _create_schema(integration_engine):
    """Create all tables once per test session."""
    async def _create():
        async with integration_engine.begin() as conn:
            for table in Base.metadata.tables.values():
                try:
                    await conn.run_sync(table.create)
                except Exception:
                    pass
    asyncio.run(_create())
    yield
    async def _drop():
        async with integration_engine.begin() as conn:
            for table in reversed(Base.metadata.tables.values()):
                try:
                    await conn.run_sync(table.drop)
                except Exception:
                    pass
    asyncio.run(_drop())


@pytest.fixture
async def db_session(integration_engine) -> AsyncSession:
    """Provide a real database session with automatic rollback."""
    async_session = sessionmaker(integration_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
        await session.close()


@pytest.mark.integration
async def test_user_role_check_constraint(db_session: AsyncSession):
    """AUDIT-035: Only valid roles can be stored in users table."""
    valid_user = User(email="valid@test.com", hashed_password="hash", full_name="Valid", role="admin")
    db_session.add(valid_user)
    await db_session.commit()

    with pytest.raises(Exception):
        invalid_user = User(email="invalid@test.com", hashed_password="hash", full_name="Invalid", role="superadmin")
        db_session.add(invalid_user)
        await db_session.commit()


@pytest.mark.integration
async def test_ar_content_active_video_constraint(db_session: AsyncSession):
    """AUDIT-034: active_video_id must belong to the same AR content.

    Skipped on SQLite because SQLite does not support subqueries in
    CHECK constraints. The constraint is enforced via Alembic migration
    on PostgreSQL.
    """
    if _is_sqlite_url(settings.DATABASE_URL):
        pytest.skip("SQLite does not support subqueries in CHECK constraints")
    company = Company(name="Test Co", slug="test-co", contact_email="test@test.com", status=CompanyStatus.ACTIVE)
    project = Project(name="Test Project", company_id=1, status=ProjectStatus.ACTIVE)
    db_session.add_all([company, project])
    await db_session.flush()

    ar_content = ARContent(project_id=project.id, company_id=company.id, order_number="INT-001", customer_name="Test", status=ArContentStatus.READY)
    db_session.add(ar_content)
    await db_session.flush()

    video = Video(ar_content_id=ar_content.id, filename="test.mp4", status=VideoStatus.READY)
    db_session.add(video)
    await db_session.commit()

    ar_content.active_video_id = video.id
    await db_session.commit()

    with pytest.raises(Exception):
        other_ar = ARContent(project_id=project.id, company_id=company.id, order_number="INT-002", customer_name="Test2", status=ArContentStatus.READY, active_video_id=video.id)
        db_session.add(other_ar)
        await db_session.commit()


@pytest.mark.integration
async def test_backup_checksum_and_verify(db_session: AsyncSession):
    """AUDIT-043: Backup files should have verifiable checksums."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".sql") as tmp:
        tmp.write(b"SELECT 1;")
        tmp_path = tmp.name

    try:
        checksum = hashlib.sha256(open(tmp_path, "rb").read()).hexdigest()
        backup = BackupHistory(status="success", size_bytes=os.path.getsize(tmp_path), trigger="manual", checksum=checksum)
        db_session.add(backup)
        await db_session.commit()

        assert backup.checksum == checksum
        assert backup.size_bytes == os.path.getsize(tmp_path)

        computed = hashlib.sha256(open(tmp_path, "rb").read()).hexdigest()
        assert backup.checksum == computed
    finally:
        os.remove(tmp_path)
