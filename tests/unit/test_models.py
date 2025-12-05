import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.company import Company

@pytest.mark.asyncio
async def test_company_create():
    async with AsyncSessionLocal() as db:  # type: AsyncSession
        company = Company(
            name="Test Company",
            slug="test-company",
            is_active=True,
        )
        db.add(company)
        await db.commit()
        await db.refresh(company)

        assert company.id is not None
        assert company.slug == "test-company"
        assert company.is_active is True
