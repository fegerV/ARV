from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import structlog

from app.core.database import get_db
from app.models.company import Company
from app.models.storage import StorageConnection
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.schemas.storage import StorageConnectionCreate
from app.services.storage.factory import StorageProviderFactory

router = APIRouter(prefix="/companies", tags=["companies"])
logger = structlog.get_logger()


@router.post("/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new company with optional storage connection."""
    try:
        # Create company
        db_company = Company(
            name=company.name,
            description=company.description,
            storage_path=company.storage_path
        )
        db.add(db_company)
        await db.commit()
        await db.refresh(db_company)

        # Handle storage connection if provided
        if company.storage_connection:
            storage_data = company.storage_connection.dict()
            storage_conn = StorageConnection(
                company_id=db_company.id,
                name=storage_data["name"],
                provider=storage_data["provider"],
                metadata=storage_data.get("credentials", {}),
                base_path=storage_data.get("base_path"),
                is_default=storage_data.get("is_default", False)
            )
            db.add(storage_conn)
            await db.commit()
            await db.refresh(storage_conn)

            # Test storage connection
            try:
                provider = StorageProviderFactory.create_provider(
                    storage_conn.provider,
                    storage_conn.metadata or {}
                )
                # Test connection
                logger.info("storage_connection_created", company_id=db_company.id, provider=storage_conn.provider)
            except Exception as e:
                logger.error("storage_connection_test_failed", error=str(e))
                # Don't fail company creation if storage test fails

        return db_company

    except Exception as e:
        await db.rollback()
        logger.error("company_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company"
        )


@router.get("/", response_model=List[CompanyResponse])
async def list_companies(include_default: bool = True, db: AsyncSession = Depends(get_db)):
    """List all companies."""
    query = select(Company)
    if not include_default:
        query = query.where(Company.is_default == False)
    query = query.order_by(Company.created_at.desc())
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get company details by ID."""
    c = await db.get(Company, company_id)
    if not c:
        raise AppException(
            status_code=404,
            detail="Company not found",
            code="COMPANY_NOT_FOUND",
        )
    return c


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update company details."""
    try:
        # Get company
        db_company = await db.get(Company, company_id)
        if not db_company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        # Update fields
        for field, value in company_update.dict(exclude_unset=True).items():
            setattr(db_company, field, value)

        await db.commit()
        await db.refresh(db_company)

        # Handle storage connection update if provided
        if company_update.storage_connection:
            storage_data = company_update.storage_connection.dict()
            
            # Check if storage connection exists
            stmt = select(StorageConnection).where(StorageConnection.company_id == company_id)
            result = await db.execute(stmt)
            storage_conn = result.scalar_one_or_none()
            
            if storage_conn:
                # Update existing storage connection
                for field, value in storage_data.items():
                    if field == "credentials":
                        storage_conn.metadata = value
                    elif hasattr(storage_conn, field):
                        setattr(storage_conn, field, value)
            else:
                # Create new storage connection
                storage_conn = StorageConnection(
                    company_id=company_id,
                    name=storage_data["name"],
                    provider=storage_data["provider"],
                    metadata=storage_data.get("credentials", {}),
                    base_path=storage_data.get("base_path"),
                    is_default=storage_data.get("is_default", False)
                )
                db.add(storage_conn)
            
            await db.commit()
            await db.refresh(storage_conn)

            # Test storage connection
            try:
                provider = StorageProviderFactory.create_provider(
                    storage_conn.provider,
                    storage_conn.metadata or {}
                )
                # Test connection
                logger.info("storage_connection_updated", company_id=company_id, provider=storage_conn.provider)
            except Exception as e:
                logger.error("storage_connection_test_failed", error=str(e))
                # Don't fail company update if storage test fails

        return db_company

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("company_update_failed", error=str(e), company_id=company_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company"
        )


@router.delete("/{company_id}")
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a company and all associated data."""
    c = await db.get(Company, company_id)
    if not c:
        raise AppException(
            status_code=404,
            detail="Company not found",
            code="COMPANY_NOT_FOUND",
        )
    
    # Trigger cleanup task for storage files
    from app.tasks.cleanup_tasks import cleanup_company_storage
    cleanup_task = cleanup_company_storage.delay(company_id)
    
    # Note: This will cascade delete all associated projects, AR content, etc.
    # due to foreign key constraints with ON DELETE CASCADE
    await db.delete(c)
    await db.commit()
    
    return {"status": "deleted", "id": company_id, "cleanup_task_id": cleanup_task.id}


@router.get("/companies/{company_id}/analytics")
async def company_analytics(company_id: int, db: AsyncSession = Depends(get_db)):
    """Get company analytics data."""
    # Placeholder: counts will require joins to ar_view_sessions
    return {
        "company_id": company_id,
        "total_views": 0,
        "unique_sessions": 0,
        "active_projects": 0,
        "active_content": 0,
    }