from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.models.storage import StorageConnection
from app.models.company import Company
# Note: schemas import removed as StorageConnection model is used directly
# from app.schemas.storage import StorageConnectionCreate, StorageConnection, CompanyStorageSettings

router = APIRouter()


@router.post("/storage/connections")
async def create_connection(
    name: str,
    provider: str,
    credentials: dict = {},
    base_path: str = None,
    is_default: bool = False,
    metadata: dict = {},
    db: AsyncSession = Depends(get_db)
):
    conn = StorageConnection(
        name=name,
        provider=provider,
        credentials=credentials,
        storage_metadata=metadata or {},
        is_active=True,
        last_tested_at=None,
        test_status=None,
        base_path=base_path,
        is_default=is_default,
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

    # For now, return a simple success response
    # TODO: Implement actual provider testing when storage providers are ready
    result = {
        "status": "success",
        "message": "Connection test not yet implemented",
        "tested_at": datetime.utcnow().isoformat()
    }

    conn.last_tested_at = datetime.utcnow()
    conn.test_status = result.get("status")
    conn.test_error = result.get("error")
    await db.commit()

    return result


@router.put("/companies/{company_id}/storage")
async def set_company_storage(
    company_id: int, 
    storage_connection_id: int = None,
    storage_path: str = None,
    db: AsyncSession = Depends(get_db)
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if storage_connection_id is not None:
        company.storage_connection_id = storage_connection_id
    if storage_path is not None:
        company.storage_path = storage_path
    await db.commit()

    return {"status": "updated"}


@router.get("/storage/connections")
async def list_storage_connections(
    provider: Optional[str] = Query(None, description="Filter by provider (local_disk, minio, yandex_disk)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List storage connections with optional filtering.
    Returns safe metadata without exposing credentials.
    """
    query = select(StorageConnection)
    
    # Apply filters
    if provider:
        query = query.where(StorageConnection.provider == provider)
    if is_active is not None:
        query = query.where(StorageConnection.is_active == is_active)
    
    query = query.order_by(StorageConnection.created_at.desc())
    
    result = await db.execute(query)
    connections = result.scalars().all()
    
    # Return safe connection data without credentials
    safe_connections = []
    for conn in connections:
        safe_conn = {
            "id": conn.id,
            "name": conn.name,
            "provider": conn.provider,
            "is_active": conn.is_active,
            "is_default": conn.is_default,
            "base_path": conn.base_path,
            "test_status": conn.test_status,
            "last_tested_at": conn.last_tested_at.isoformat() if conn.last_tested_at else None,
            "created_at": conn.created_at.isoformat() if conn.created_at else None,
            "updated_at": conn.updated_at.isoformat() if conn.updated_at else None,
            "metadata": conn.storage_metadata or {},
        }
        
        # Add provider-specific safe metadata
        if conn.provider == "yandex_disk" and conn.storage_metadata:
            safe_conn["user_display_name"] = conn.storage_metadata.get("user_display_name")
            safe_conn["total_space"] = conn.storage_metadata.get("total_space")
            safe_conn["used_space"] = conn.storage_metadata.get("used_space")
            safe_conn["has_encryption"] = conn.storage_metadata.get("has_encryption", False)
        
        safe_connections.append(safe_conn)
    
    return {
        "connections": safe_connections,
        "total": len(safe_connections),
        "filters": {
            "provider": provider,
            "is_active": is_active,
        }
    }
