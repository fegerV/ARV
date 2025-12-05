from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.models.storage import StorageConnection
from app.models.company import Company
from app.schemas.storage import StorageConnectionCreate, StorageConnectionResponse, CompanyStorageSettings
from app.services.storage.factory import get_provider

router = APIRouter()


@router.post("/storage/connections", response_model=StorageConnectionResponse)
async def create_connection(payload: StorageConnectionCreate, db: AsyncSession = Depends(get_db)):
    conn = StorageConnection(
        name=payload.name,
        provider=payload.provider,
        credentials=payload.credentials,
        is_active=True,
        last_tested_at=None,
        test_status=None,
        base_path=payload.base_path,
        is_default=payload.is_default,
    )
    db.add(conn)
    await db.flush()
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/storage/connections/{connection_id}/test")
async def test_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    provider = get_provider(conn)
    result = await provider.test_connection()

    conn.last_tested_at = datetime.utcnow()
    conn.test_status = result.get("status")
    conn.test_error = result.get("error")
    await db.commit()

    return result


@router.put("/companies/{company_id}/storage")
async def set_company_storage(company_id: int, settings: CompanyStorageSettings, db: AsyncSession = Depends(get_db)):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company.storage_connection_id = settings.storage_connection_id
    company.storage_path = settings.storage_path
    await db.commit()

    return {"status": "updated"}
