"""
Storage-related background tasks.
"""

import logging
import shutil
from pathlib import Path
from typing import BinaryIO, Optional, Union

from fastapi import BackgroundTasks, UploadFile

from app.core.config import settings
from app.core.storage import get_storage_provider
from . import run_background_task

logger = logging.getLogger(__name__)


async def save_upload_file(
    background_tasks: BackgroundTasks,
    file: Union[UploadFile, BinaryIO],
    destination: str,
    content_type: Optional[str] = None
) -> str:
    """
    Save an uploaded file to storage in the background.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        file: The uploaded file or file-like object
        destination: Destination path in storage
        content_type: Optional content type of the file
        
    Returns:
        The path where the file was saved
    """
    # If it's an UploadFile, we need to read its contents
    if hasattr(file, 'file'):  # It's an UploadFile
        content = await file.read()
        filename = file.filename
        if content_type is None:
            content_type = file.content_type
    else:  # It's a file-like object
        content = file.read()
        filename = getattr(file, 'name', 'file')
    
    # Run the actual file save in the background
    await run_background_task(
        background_tasks,
        _save_file_content,
        content=content,
        destination=destination,
        filename=filename,
        content_type=content_type
    )
    
    logger.info("file_save_queued", destination=destination, filename=filename)
    return destination


def _save_file_content(
    content: bytes,
    destination: str,
    filename: str,
    content_type: Optional[str] = None
) -> str:
    """
    Save file content to storage (runs in a background thread).
    
    Args:
        content: File content as bytes
        destination: Destination path in storage
        filename: Original filename
        content_type: Optional content type
        
    Returns:
        The path where the file was saved
    """
    storage = get_storage_provider()
    
    # Ensure the destination directory exists
    dest_path = Path(settings.LOCAL_STORAGE_PATH) / destination
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save the file
    with open(dest_path, 'wb') as f:
        f.write(content)
    
    logger.info("file_saved", path=str(dest_path), size=len(content))
    return str(dest_path)


async def delete_file(
    background_tasks: BackgroundTasks,
    file_path: str
) -> None:
    """
    Delete a file in the background.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        file_path: Path to the file to delete
    """
    await run_background_task(background_tasks, _delete_file, file_path)
    logger.info("file_deletion_queued", path=file_path)


def _delete_file(file_path: str) -> None:
    """
    Delete a file (runs in a background thread).
    
    Args:
        file_path: Path to the file to delete
    """
    try:
        path = Path(file_path)
        if path.exists():
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            logger.info("file_deleted", path=file_path)
        else:
            logger.warning("file_not_found_for_deletion", path=file_path)
    except Exception as e:
        logger.error("file_deletion_failed", path=file_path, error=str(e))
        raise


async def cleanup_temp_files(
    background_tasks: BackgroundTasks,
    directory: str,
    pattern: str = "*",
    max_age_seconds: int = 86400  # 24 hours
) -> None:
    """
    Clean up temporary files in a directory that are older than max_age_seconds.
    
    Args:
        background_tasks: FastAPI BackgroundTasks instance
        directory: Directory to clean up
        pattern: File pattern to match (e.g., "*.tmp")
        max_age_seconds: Maximum age of files to keep (in seconds)
    """
    await run_background_task(
        background_tasks,
        _cleanup_temp_files,
        directory=directory,
        pattern=pattern,
        max_age_seconds=max_age_seconds
    )


def _cleanup_temp_files(directory: str, pattern: str, max_age_seconds: int) -> None:
    """
    Clean up temporary files (runs in a background thread).
    
    Args:
        directory: Directory to clean up
        pattern: File pattern to match
        max_age_seconds: Maximum age of files to keep (in seconds)
    """
    import time
    from pathlib import Path
    
    now = time.time()
    deleted = 0
    
    try:
        path = Path(directory)
        if not path.exists() or not path.is_dir():
            logger.warning("cleanup_directory_not_found", directory=directory)
            return
            
        for file_path in path.glob(pattern):
            try:
                file_age = now - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    if file_path.is_file():
                        file_path.unlink()
                        deleted += 1
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                        deleted += 1
            except Exception as e:
                logger.error("cleanup_file_failed", path=str(file_path), error=str(e))
        
        logger.info("cleanup_completed", directory=directory, files_deleted=deleted)
    except Exception as e:
        logger.error("cleanup_failed", directory=directory, error=str(e))
