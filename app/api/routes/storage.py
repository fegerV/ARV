from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.storage import get_storage_provider_instance
from app.models.storage import StorageConnection
from app.models.company import Company
from app.schemas.storage import StorageConnectionCreate, StorageConnectionUpdate, StorageUsageStats

router = APIRouter()


@router.post("/storage/connections")
async def create_connection(
    connection_data: StorageConnectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new local storage connection."""
    conn = StorageConnection(
        name=connection_data.name,
        provider="local_disk",  # Always local_disk now
        base_path=connection_data.base_path,
        is_active=True,
        is_default=connection_data.is_default,
        storage_metadata={},
    )
    db.add(conn)
    await db.flush()
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/storage/connections/{connection_id}/test")
async def test_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Test a storage connection."""
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        # Test local storage by checking if base path exists and is accessible
        from pathlib import Path
        base_path = Path(conn.base_path)
        
        if not base_path.exists():
            result = {
                "status": "error",
                "message": f"Base path does not exist: {conn.base_path}",
                "tested_at": datetime.utcnow().isoformat()
            }
        elif not base_path.is_dir():
            result = {
                "status": "error", 
                "message": f"Base path is not a directory: {conn.base_path}",
                "tested_at": datetime.utcnow().isoformat()
            }
        else:
            # Try to create a test file
            try:
                test_file = base_path / ".storage_test"
                test_file.write_text("test")
                test_file.unlink()
                
                result = {
                    "status": "success",
                    "message": "Local storage connection test successful",
                    "tested_at": datetime.utcnow().isoformat(),
                    "base_path": str(base_path),
                    "writable": True
                }
            except Exception as e:
                result = {
                    "status": "error",
                    "message": f"Base path is not writable: {str(e)}",
                    "tested_at": datetime.utcnow().isoformat()
                }
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Connection test failed: {str(e)}",
            "tested_at": datetime.utcnow().isoformat()
        }

    conn.last_tested_at = datetime.utcnow()
    conn.test_status = result.get("status")
    conn.test_error = result.get("message") if result.get("status") == "error" else None
    await db.commit()

    return result


@router.get("/storage/connections/{connection_id}/stats")
async def get_storage_stats(connection_id: int, path: str = "", db: AsyncSession = Depends(get_db)):
    """Get storage usage statistics for a connection."""
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Use the storage provider to get stats
    storage_provider = get_storage_provider_instance()
    stats = await storage_provider.get_usage_stats(path)
    
    return StorageUsageStats(**stats)


@router.put("/companies/{company_id}/storage")
async def set_company_storage(
    company_id: int, 
    storage_connection_id: int = None,
    storage_path: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Set storage configuration for a company."""
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
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    """
    List local storage connections with optional filtering.
    Returns safe metadata without exposing sensitive information.
    """
    query = select(StorageConnection).where(StorageConnection.provider == "local_disk")
    
    # Apply filters
    if is_active is not None:
        query = query.where(StorageConnection.is_active == is_active)
    
    query = query.order_by(StorageConnection.created_at.desc())
    
    result = await db.execute(query)
    connections = result.scalars().all()
    
    # Return safe connection data
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
        safe_connections.append(safe_conn)
    
    return {
        "connections": safe_connections,
        "total": len(safe_connections),
        "filters": {
            "is_active": is_active,
        }
    }
