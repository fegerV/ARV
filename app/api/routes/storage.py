from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
import structlog
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.storage import StorageConnection
from app.models.company import Company
from app.schemas.storage import (
    StorageConnectionCreate, 
    StorageConnectionResponse,
    PresignedURLRequest,
    PresignedURLResponse
)
from app.services.storage.factory import StorageProviderFactory

router = APIRouter(prefix="/storage", tags=["storage"])
logger = structlog.get_logger()

@router.get("/connections", response_model=List[StorageConnectionResponse])
async def list_storage_connections(db: AsyncSession = Depends(get_db)):
    """List all storage connections."""
    query = select(StorageConnection).order_by(StorageConnection.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/connections/{connection_id}", response_model=StorageConnectionResponse)
async def get_storage_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific storage connection by ID."""
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Storage connection not found")
    return conn


@router.post("/connections/", response_model=StorageConnectionResponse)
async def create_storage_connection(
    storage: StorageConnectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new storage connection."""
    try:
        # Create storage connection
        db_storage = StorageConnection(
            name=storage.name,
            provider=storage.provider,
            connection_metadata=storage.credentials or {},
            base_path=storage.base_path,
            is_default=storage.is_default
        )
        db.add(db_storage)
        await db.commit()
        await db.refresh(db_storage)
        
        # Test connection
        try:
            provider = StorageProviderFactory.create_provider(
                db_storage.provider,
                db_storage.connection_metadata or {}
            )
            # Test connection
            logger.info("storage_connection_created", storage_id=db_storage.id, provider=db_storage.provider)
        except Exception as e:
            logger.error("storage_connection_test_failed", error=str(e))
            # Don't fail creation if test fails
            
        return db_storage
        
    except Exception as e:
        await db.rollback()
        logger.error("storage_connection_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create storage connection"
        )


@router.put("/connections/{connection_id}", response_model=StorageConnectionResponse)
async def update_storage_connection(
    connection_id: int,
    storage: StorageConnectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing storage connection."""
    try:
        # Get storage connection
        conn = await db.get(StorageConnection, connection_id)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage connection not found"
            )
        
        # Update fields
        conn.name = storage.name
        conn.provider = storage.provider
        conn.connection_metadata = storage.credentials or {}
        conn.base_path = storage.base_path
        conn.is_default = storage.is_default
        conn.updated_at = datetime.utcnow()
        
        # Test connection
        try:
            provider = StorageProviderFactory.create_provider(
                conn.provider,
                conn.connection_metadata or {}
            )
            # Test connection
            logger.info("storage_connection_updated", storage_id=conn.id, provider=conn.provider)
        except Exception as e:
            logger.error("storage_connection_test_failed", error=str(e))
            # Don't fail creation if test fails
            
        await db.commit()
        await db.refresh(conn)
        return conn
        
    except Exception as e:
        await db.rollback()
        logger.error("storage_connection_update_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update storage connection"
        )


@router.delete("/connections/{connection_id}")
async def delete_storage_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a storage connection."""
    try:
        # Get storage connection
        conn = await db.get(StorageConnection, connection_id)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage connection not found"
            )
        
        # Check if connection is used by any company
        company_count = await db.execute(
            select(func.count()).select_from(Company).where(Company.storage_connection_id == connection_id)
        )
        if company_count.scalar() > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete connection that is used by companies"
            )
        
        # Check if it's a default connection
        if conn.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default connection"
            )
        
        await db.delete(conn)
        await db.commit()
        return {"status": "deleted", "id": connection_id}
        
    except Exception as e:
        await db.rollback()
        logger.error("storage_connection_deletion_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete storage connection"
        )


@router.post("/minio/presign-upload", response_model=PresignedURLResponse)
async def generate_minio_presigned_url(
    request: PresignedURLRequest,
    connection_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate a presigned URL for direct MinIO upload."""
    try:
        # Get storage connection
        conn = await db.get(StorageConnection, connection_id)
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Storage connection not found"
            )
            
        # Ensure it's a MinIO connection
        if conn.provider != "minio":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Connection is not a MinIO connection"
            )
            
        # Create provider
        provider = StorageProviderFactory.create_provider(
            conn.provider,
            conn.connection_metadata or {}
        )
        
        # Generate presigned URL
        url = await provider.generate_presigned_url(
            remote_path=request.object_name,
            expires_in=request.expires_in or 3600,
            method=request.method or "PUT"
        )
        
        logger.info(
            "minio_presigned_url_generated",
            connection_id=connection_id,
            object_name=request.object_name,
            url=url
        )
        
        return PresignedURLResponse(
            url=url,
            method=request.method or "PUT",
            expires_at=datetime.utcnow().timestamp() + (request.expires_in or 3600),
            fields={}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("minio_presigned_url_generation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate presigned URL"
        )
