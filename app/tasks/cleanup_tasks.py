"""
Celery tasks for cleaning up storage files when content is deleted.
These tasks handle the removal of files from storage providers when
AR content or videos are deleted from the database.
"""

import asyncio
import structlog
from celery import Celery
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.company import Company
from app.models.storage import StorageConnection
from app.services.storage.factory import StorageProviderFactory

logger = structlog.get_logger()

celery_app = Celery(__name__, broker=settings.CELERY_BROKER_URL)


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_expired_content")
def cleanup_expired_content():
    """Clean up expired AR content and associated files."""
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            try:
                # Get all companies with storage connections
                companies = await db.execute(select(Company))
                companies = companies.scalars().all()
                
                for company in companies:
                    # Get storage connection
                    storage_conn = await db.get(StorageConnection, company.storage_connection_id)
                    if not storage_conn:
                        continue
                        
                    # Create provider
                    try:
                        provider = StorageProviderFactory.create_provider(
                            storage_conn.provider,
                            storage_conn.connection_metadata or {}
                        )
                    except Exception as e:
                        logger.error(
                            "storage_provider_creation_failed",
                            company_id=company.id,
                            provider=storage_conn.provider,
                            error=str(e)
                        )
                        continue
                    
                    # Clean up expired content
                    base_path = (company.storage_path or "/").rstrip("/")
                    expired_folder = f"{base_path}/ar_content/expired"
                    
                    # List files in the expired folder
                    files = await provider.list_files(expired_folder)
                    
                    for file in files:
                        try:
                            # Extract the file path
                            file_path = f"{expired_folder}/{file}"
                            
                            # Delete the file
                            await provider.delete_file(file_path)
                            
                            logger.info(
                                "cleanup_expired_content_completed",
                                company_id=company.id,
                                file_path=file_path
                            )
                        except Exception as e:
                            logger.error(
                                "cleanup_expired_content_failed",
                                company_id=company.id,
                                file_path=file_path,
                                error=str(e)
                            )
                    
            except Exception as e:
                logger.error("cleanup_expired_content_failed", error=str(e))
                raise
                
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_temp_files")
def cleanup_temp_files():
    """Clean up temporary files."""
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            try:
                # Get all companies with storage connections
                companies = await db.execute(select(Company))
                companies = companies.scalars().all()
                
                for company in companies:
                    # Get storage connection
                    storage_conn = await db.get(StorageConnection, company.storage_connection_id)
                    if not storage_conn:
                        continue
                        
                    # Create provider
                    try:
                        provider = StorageProviderFactory.create_provider(
                            storage_conn.provider,
                            storage_conn.connection_metadata or {}
                        )
                    except Exception as e:
                        logger.error(
                            "storage_provider_creation_failed",
                            company_id=company.id,
                            provider=storage_conn.provider,
                            error=str(e)
                        )
                        continue
                    
                    # Clean up temp files
                    base_path = (company.storage_path or "/").rstrip("/")
                    temp_folder = f"{base_path}/temp"
                    
                    # List files in the temp folder
                    files = await provider.list_files(temp_folder)
                    
                    for file in files:
                        try:
                            # Extract the file path
                            file_path = f"{temp_folder}/{file}"
                            
                            # Delete the file
                            await provider.delete_file(file_path)
                            
                            logger.info(
                                "cleanup_temp_files_completed",
                                company_id=company.id,
                                file_path=file_path
                            )
                        except Exception as e:
                            logger.error(
                                "cleanup_temp_files_failed",
                                company_id=company.id,
                                file_path=file_path,
                                error=str(e)
                            )
                    
            except Exception as e:
                logger.error("cleanup_temp_files_failed", error=str(e))
                raise
                
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        loop.close()


@celery_app.task(name="app.tasks.cleanup_tasks.cleanup_orphaned_files")
def cleanup_orphaned_files():
    """Clean up orphaned files that are no longer referenced."""
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            try:
                # Get all companies with storage connections
                companies = await db.execute(select(Company))
                companies = companies.scalars().all()
                
                for company in companies:
                    # Get storage connection
                    storage_conn = await db.get(StorageConnection, company.storage_connection_id)
                    if not storage_conn:
                        continue
                        
                    # Create provider
                    try:
                        provider = StorageProviderFactory.create_provider(
                            storage_conn.provider,
                            storage_conn.connection_metadata or {}
                        )
                    except Exception as e:
                        logger.error(
                            "storage_provider_creation_failed",
                            company_id=company.id,
                            provider=storage_conn.provider,
                            error=str(e)
                        )
                        continue
                    
                    # Clean up orphaned files
                    base_path = (company.storage_path or "/").rstrip("/")
                    orphaned_folder = f"{base_path}/orphaned"
                    
                    # List files in the orphaned folder
                    files = await provider.list_files(orphaned_folder)
                    
                    for file in files:
                        try:
                            # Extract the file path
                            file_path = f"{orphaned_folder}/{file}"
                            
                            # Delete the file
                            await provider.delete_file(file_path)
                            
                            logger.info(
                                "cleanup_orphaned_files_completed",
                                company_id=company.id,
                                file_path=file_path
                            )
                        except Exception as e:
                            logger.error(
                                "cleanup_orphaned_files_failed",
                                company_id=company.id,
                                file_path=file_path,
                                error=str(e)
                            )
                    
            except Exception as e:
                logger.error("cleanup_orphaned_files_failed", error=str(e))
                raise
                
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_cleanup())
    finally:
        loop.close()
