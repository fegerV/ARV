from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import structlog

from app.core.database import get_db
from app.core.errors import AppException
from app.models.company import Company
from app.models.storage import StorageConnection
from app.schemas.company import CompanyCreate, CompanyUpdate, CompanyResponse
from app.utils.slugify import slugify, generate_unique_slug

router = APIRouter(prefix="/companies", tags=["companies"])
logger = structlog.get_logger()


@router.post("/", response_model=CompanyResponse)
async def create_company(
    company: CompanyCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new company with storage connection."""
    try:
        # Validate storage connection exists
        storage_conn = await db.get(StorageConnection, company.storage_connection_id)
        if not storage_conn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage connection with ID {company.storage_connection_id} not found"
            )

        # Generate slug
        base_slug = slugify(company.name)
        
        # Check for existing slugs and generate unique one
        stmt = select(Company.slug).where(Company.slug.ilike(f"{base_slug}%"))
        result = await db.execute(stmt)
        existing_slugs = [row[0] for row in result.fetchall()]
        unique_slug = generate_unique_slug(company.name, existing_slugs)

        # Generate storage path if not provided
        storage_path = company.storage_path or f"/companies/{unique_slug}"

        # Create company
        db_company = Company(
            name=company.name,
            slug=unique_slug,
            description=company.notes,  # Using notes as description for now
            storage_connection_id=company.storage_connection_id,
            storage_path=storage_path,
            contact_email=company.contact_email,
            contact_phone=company.contact_phone,
            telegram_chat_id=company.telegram_chat_id,
            subscription_tier=company.subscription_tier,
            subscription_expires_at=company.subscription_expires_at,
            storage_quota_gb=company.storage_quota_gb,
            projects_limit=company.projects_limit,
            notes=company.notes,
        )
        db.add(db_company)
        await db.commit()
        await db.refresh(db_company)

        logger.info("company_created", company_id=db_company.id, slug=unique_slug)
        return db_company

    except HTTPException:
        raise
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

        # Validate storage connection exists if provided
        if company_update.storage_connection_id is not None:
            storage_conn = await db.get(StorageConnection, company_update.storage_connection_id)
            if not storage_conn:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Storage connection with ID {company_update.storage_connection_id} not found"
                )

        # Generate new slug if name is being updated
        update_data = company_update.dict(exclude_unset=True)
        if "name" in update_data and update_data["name"] != db_company.name:
            base_slug = slugify(update_data["name"])
            
            # Check for existing slugs and generate unique one
            stmt = select(Company.slug).where(
                Company.slug.ilike(f"{base_slug}%"),
                Company.id != company_id
            )
            result = await db.execute(stmt)
            existing_slugs = [row[0] for row in result.fetchall()]
            update_data["slug"] = generate_unique_slug(update_data["name"], existing_slugs)

        # Update fields
        for field, value in update_data.items():
            setattr(db_company, field, value)

        await db.commit()
        await db.refresh(db_company)

        logger.info("company_updated", company_id=company_id)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    # Trigger cleanup task for storage files
    try:
        from app.tasks.cleanup_tasks import cleanup_company_storage
        cleanup_task = cleanup_company_storage.delay(company_id)
        cleanup_task_id = cleanup_task.id
    except Exception as e:
        logger.warning("cleanup_task_failed", error=str(e), company_id=company_id)
        cleanup_task_id = None
    
    # Note: This will cascade delete all associated projects, AR content, etc.
    # due to foreign key constraints with ON DELETE CASCADE
    await db.delete(c)
    await db.commit()
    
    response = {"status": "deleted", "id": company_id}
    if cleanup_task_id:
        response["cleanup_task_id"] = cleanup_task_id
    
    return response


@router.get("/{company_id}/analytics")
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