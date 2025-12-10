from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.database import get_db
from app.models.company import Company
from app.models.storage import StorageConnection
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyResponse
from app.services.storage.factory import get_provider
from app.api.routes.auth import get_current_active_user

router = APIRouter(tags=["companies"])

@router.post("/", response_model=CompanyResponse)
async def create_company(
    company_data: CompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    logger = structlog.get_logger()
    # ВАЖНО: Требуем storage_connection_id
    storage_conn = await db.get(StorageConnection, company_data.storage_connection_id)
    if not storage_conn:
        raise HTTPException(status_code=404, detail="Storage connection not found")
    if getattr(storage_conn, "is_default", False):
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot use default Vertex AR storage for client companies. "
                "Please create a new storage connection (MinIO or Yandex Disk)."
            ),
        )

    # Генерируем slug
    slug = company_data.name.lower().replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    # Проверяем уникальность
    exists = await db.execute(select(Company).where(Company.slug == slug))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Company with slug '{slug}' already exists")

    # Создаем папку в хранилище
    storage_path = f"/Companies/{company_data.name}"
    provider = get_provider(storage_conn)
    result = await provider.create_folder(storage_path)
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create folder in {storage_conn.provider}: {result.get('error')}",
        )

    # Создаем компанию
    company = Company(
        name=company_data.name,
        slug=slug,
        contact_email=company_data.contact_email,
        contact_phone=company_data.contact_phone,
        telegram_chat_id=company_data.telegram_chat_id,
        storage_connection_id=company_data.storage_connection_id,
        storage_path=storage_path,
        subscription_tier=company_data.subscription_tier,
        subscription_expires_at=company_data.subscription_expires_at,
        storage_quota_gb=company_data.storage_quota_gb,
        projects_limit=company_data.projects_limit,
        notes=company_data.notes,
        is_default=False,
    )
    db.add(company)
    await db.commit()
    await db.refresh(company)

    logger.info("company_created", company_id=company.id, name=company.name, storage_provider=storage_conn.provider)
    return company

@router.get("/", response_model=List[CompanyResponse])
async def list_companies(include_default: bool = False, db: AsyncSession = Depends(get_db)):
    query = select(Company)
    if not include_default:
        query = query.where(Company.is_default == False)
    query = query.order_by(Company.created_at.desc())
    res = await db.execute(query)
    return res.scalars().all()

@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    c = await db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    return c

@router.put("/{company_id}")
async def update_company(
    company_id: int, 
    payload: dict, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    c = await db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    for k, v in payload.items():
        if hasattr(c, k):
            setattr(c, k, v)
    await db.commit()
    return {"status": "updated"}

@router.delete("/{company_id}")
async def delete_company(
    company_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    c = await db.get(Company, company_id)
    if not c:
        raise HTTPException(status_code=404, detail="Company not found")
    await db.delete(c)
    await db.commit()
    return {"status": "deleted"}

@router.get("/{company_id}/analytics")
async def company_analytics(company_id: int, db: AsyncSession = Depends(get_db)):    
    # Placeholder: counts will require joins to ar_view_sessions
    return {
        "company_id": company_id,
        "total_views": 0,
        "unique_sessions": 0,
        "active_projects": 0,
        "active_content": 0,
    }