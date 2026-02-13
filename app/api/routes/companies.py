from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
import httpx
import structlog

from app.core.config import get_settings
from app.core.database import get_db
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.user import User
from app.schemas.company_api import (
    CompanyCreate, CompanyUpdate, CompanyListItem, CompanyDetail,
    CompanyLinks, PaginatedCompaniesResponse
)
from app.api.routes.auth import get_current_active_user
from app.utils.slug_utils import generate_slug
from app.utils.token_encryption import token_encryption

router = APIRouter(tags=["companies"])


def _generate_company_links(company_id: int) -> CompanyLinks:
    """Generate HATEOAS links for a company"""
    return CompanyLinks(
        edit=f"/companies/{company_id}",
        delete=f"/companies/{company_id}",
        view_projects=f"/companies/{company_id}/projects",
        view_content=f"/companies/{company_id}/ar-content"
    )


@router.get("/companies", response_model=PaginatedCompaniesResponse)
async def list_companies(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(default=None, description="Search by name or email"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # Validate page_size - only allow 20, 30, 40, 50
    if page_size not in [20, 30, 40, 50]:
        page_size = 20
    """List companies with pagination and filtering"""
    import structlog
    logger = structlog.get_logger()
    
    # Build base query
    query = select(Company)
    count_query = select(func.count()).select_from(Company)
    
    # Apply filters
    where_conditions = []
    
    if search:
        search_condition = or_(
            Company.name.ilike(f"%{search}%"),
            Company.contact_email.ilike(f"%{search}%")
        )
        where_conditions.append(search_condition)
    
    if status:
        where_conditions.append(Company.status == status)
    
    if where_conditions:
        query = query.where(*where_conditions)
        count_query = count_query.where(*where_conditions)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Apply pagination and ordering
    query = query.order_by(Company.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    companies = result.scalars().all()
    
    # Optimize projects count: load all counts in one query
    company_ids = [c.id for c in companies]
    projects_counts = {}
    if company_ids:
        # Single query to get all project counts grouped by company_id
        projects_count_query = (
            select(Project.company_id, func.count(Project.id).label('count'))
            .where(Project.company_id.in_(company_ids))
            .group_by(Project.company_id)
        )
        projects_count_result = await db.execute(projects_count_query)
        for row in projects_count_result.all():
            projects_counts[row.company_id] = row.count
    
    # Build response items
    items = []
    for company in companies:
        item = CompanyListItem(
            id=str(company.id),
            name=company.name,
            contact_email=company.contact_email,
            storage_provider=company.storage_provider or "local",
            status=company.status,
            projects_count=projects_counts.get(company.id, 0),
            created_at=company.created_at,
            _links=_generate_company_links(company.id)
        )
        items.append(item)
    
    logger.info("companies_listed", total=total, page=page, page_size=page_size)
    
    return PaginatedCompaniesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/companies/{company_id}", response_model=CompanyDetail)
async def get_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed company information"""
    # Get company
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get projects count
    projects_count_query = select(func.count()).select_from(Project).where(Project.company_id == company.id)
    projects_count_result = await db.execute(projects_count_query)
    projects_count = projects_count_result.scalar()
    
    # Get AR content count
    ar_content_query = (
        select(func.count())
        .select_from(ARContent)
        .join(Project)
        .where(Project.company_id == company_id)
    )
    ar_content_result = await db.execute(ar_content_query)
    ar_content_count = ar_content_result.scalar()
    
    return CompanyDetail(
        id=str(company.id),
        name=company.name,
        contact_email=company.contact_email,
        storage_provider=company.storage_provider or "local",
        yandex_connected=bool(company.yandex_disk_token),
        status=company.status,
        projects_count=projects_count,
        ar_content_count=ar_content_count,
        created_at=company.created_at,
        _links=_generate_company_links(company_id)
    )


@router.post("/companies", response_model=CompanyDetail)
async def create_company(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new company"""
    logger = structlog.get_logger()
    
    # Prevent creating duplicate default company
    DEFAULT_COMPANY_NAMES = ["Vertex AR", "VertexAR", "vertex-ar", "vertexar"]
    company_name_normalized = company_data.name.strip()
    
    # Check if trying to create default company
    if any(company_name_normalized.lower() == default_name.lower() for default_name in DEFAULT_COMPANY_NAMES):
        # Check if default company already exists
        existing_default = await db.execute(
            select(Company).where(
                func.lower(Company.name).in_([name.lower() for name in DEFAULT_COMPANY_NAMES])
            )
        )
        if existing_default.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Default company 'Vertex AR' already exists. You cannot create duplicate default companies."
            )
    
    # Check for duplicate name (case-insensitive)
    existing_company = await db.execute(
        select(Company).where(func.lower(Company.name) == company_name_normalized.lower())
    )
    if existing_company.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Company with name '{company_data.name}' already exists"
        )
    
    # Generate slug from company name
    slug = generate_slug(company_data.name)
    
    # Check for duplicate slug
    existing_slug = await db.execute(select(Company).where(Company.slug == slug))
    if existing_slug.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Company with slug '{slug}' already exists"
        )
    
    # Create company
    company = Company(
        name=company_name_normalized,
        slug=slug,
        contact_email=company_data.contact_email,
        status=company_data.status,
        storage_provider=company_data.storage_provider.value,
    )
    
    db.add(company)
    await db.commit()
    await db.refresh(company)
    
    logger.info("company_created", company_id=company.id, name=company.name,
                storage_provider=company.storage_provider)
    
    return CompanyDetail(
        id=str(company.id),
        name=company.name,
        contact_email=company.contact_email,
        storage_provider=company.storage_provider or "local",
        yandex_connected=bool(company.yandex_disk_token),
        status=company.status,
        projects_count=0,
        ar_content_count=0,
        created_at=company.created_at,
        _links=_generate_company_links(company.id)
    )


@router.put("/companies/{company_id}", response_model=CompanyDetail)
async def update_company(
    company_id: int,
    company_data: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update company information"""
    logger = structlog.get_logger()
    
    # Get company
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Update fields
    update_data = company_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)
    
    await db.commit()
    await db.refresh(company)
    
    # Get counts for response
    projects_count_query = select(func.count()).select_from(Project).where(Project.company_id == company.id)
    projects_count_result = await db.execute(projects_count_query)
    projects_count = projects_count_result.scalar()
    
    ar_content_query = (
        select(func.count())
        .select_from(ARContent)
        .join(Project)
        .where(Project.company_id == company_id)
    )
    ar_content_result = await db.execute(ar_content_query)
    ar_content_count = ar_content_result.scalar()
    
    logger.info("company_updated", company_id=company.id)
    
    return CompanyDetail(
        id=str(company.id),
        name=company.name,
        contact_email=company.contact_email,
        storage_provider=company.storage_provider or "local",
        yandex_connected=bool(company.yandex_disk_token),
        status=company.status,
        projects_count=projects_count,
        ar_content_count=ar_content_count,
        created_at=company.created_at,
        _links=_generate_company_links(company_id)
    )


@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a company (with dependency checks)"""
    logger = structlog.get_logger()
    
    # Get company
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check for dependencies
    projects_count_query = select(func.count()).select_from(Project).where(Project.company_id == company.id)
    projects_count_result = await db.execute(projects_count_query)
    projects_count = projects_count_result.scalar()
    
    if projects_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete company with {projects_count} projects. Delete projects first."
        )
    
    # Delete company
    await db.delete(company)
    await db.commit()
    
    logger.info("company_deleted", company_id=company_id, name=company.name)
    
    return {"status": "deleted"}


# ------------------------------------------------------------------
# Yandex Disk OAuth flow
# ------------------------------------------------------------------

@router.get("/companies/{company_id}/yandex-auth-url")
async def get_yandex_auth_url(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Generate Yandex OAuth authorization URL for a company.

    The user opens this URL in a new tab, authorizes, and copies the
    verification code back into the admin panel form.
    """
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    cfg = get_settings()
    if not cfg.YANDEX_OAUTH_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="YANDEX_OAUTH_CLIENT_ID is not configured on the server",
        )

    auth_url = (
        "https://oauth.yandex.ru/authorize"
        f"?response_type=code"
        f"&client_id={cfg.YANDEX_OAUTH_CLIENT_ID}"
        f"&redirect_uri=https://oauth.yandex.ru/verification_code"
        f"&force_confirm=yes"
    )
    return {"auth_url": auth_url, "company_id": company_id}


class YandexAuthCodePayload(BaseModel):
    """Payload for exchanging Yandex OAuth code."""
    code: str


@router.post("/companies/{company_id}/yandex-auth-code")
async def exchange_yandex_auth_code(
    company_id: int,
    payload: YandexAuthCodePayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Exchange Yandex OAuth verification code for an access token.

    Encrypts the token and saves it in the ``companies.yandex_disk_token``
    column.  Yandex OAuth tokens are permanent — no refresh needed.
    """
    logger = structlog.get_logger()
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    cfg = get_settings()
    if not cfg.YANDEX_OAUTH_CLIENT_ID or not cfg.YANDEX_OAUTH_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Yandex OAuth credentials are not configured",
        )

    # Exchange the code for an access token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://oauth.yandex.ru/token",
                data={
                    "grant_type": "authorization_code",
                    "code": payload.code,
                    "client_id": cfg.YANDEX_OAUTH_CLIENT_ID,
                    "client_secret": cfg.YANDEX_OAUTH_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                detail = resp.json().get("error_description", resp.text)
                logger.error("yandex_token_exchange_failed", status=resp.status_code, detail=detail)
                raise HTTPException(
                    status_code=400,
                    detail=f"Yandex OAuth error: {detail}",
                )
            token_data = resp.json()
    except httpx.HTTPError as exc:
        logger.error("yandex_token_exchange_http_error", error=str(exc))
        raise HTTPException(status_code=502, detail=f"Failed to reach Yandex OAuth: {exc}")

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access_token in Yandex response")

    # Encrypt and persist
    encrypted = token_encryption.encrypt_credentials({"access_token": access_token})
    company.yandex_disk_token = encrypted
    company.storage_provider = "yandex_disk"
    await db.commit()
    await db.refresh(company)

    logger.info("yandex_disk_connected", company_id=company_id)

    return {
        "status": "connected",
        "company_id": company_id,
        "storage_provider": company.storage_provider,
    }


@router.delete("/companies/{company_id}/yandex-token")
async def delete_yandex_token(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Disconnect Yandex Disk from the company and delete the stored token."""
    logger = structlog.get_logger()
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.yandex_disk_token = None
    company.storage_provider = "local"
    await db.commit()
    await db.refresh(company)

    logger.info("yandex_disk_disconnected", company_id=company_id)
    return {
        "status": "disconnected",
        "company_id": company_id,
        "storage_provider": company.storage_provider,
    }
