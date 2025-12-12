"""
AR Content utilities for storage paths and QR code generation.
"""
import uuid
from pathlib import Path
from typing import Optional
import qrcode
from PIL import Image
import io
import aiofiles

from app.core.config import settings


def build_ar_content_storage_path(company_id: int, project_id: int, unique_id: uuid.UUID) -> Path:
    """Build the storage path for AR content following the new hierarchy.
    
    Args:
        company_id: The company ID
        project_id: The project ID  
        unique_id: The unique UUID for the AR content
        
    Returns:
        Path object for the AR content storage directory
    """
    return (
        Path(settings.STORAGE_BASE_PATH) /
        "companies" / str(company_id) /
        "projects" / str(project_id) /
        "ar-content" / str(unique_id)
    )


def build_public_url(storage_path: Path) -> str:
    """Convert a storage path to a public URL.
    
    Args:
        storage_path: The absolute storage path
        
    Returns:
        Public URL starting with /storage/
    """
    base_path = Path(settings.STORAGE_BASE_PATH)
    relative_path = storage_path.relative_to(base_path)
    return f"/storage/{relative_path.as_posix()}"


def build_unique_link(unique_id: uuid.UUID) -> str:
    """Build the unique public link for AR content.
    
    Args:
        unique_id: The unique UUID for the AR content
        
    Returns:
        Public link URL
    """
    return f"/ar-content/{unique_id}"


async def generate_qr_code(unique_id: uuid.UUID, storage_path: Path) -> str:
    """Generate QR code for AR content and save it to storage.
    
    Args:
        unique_id: The unique UUID for the AR content
        storage_path: The storage directory path for the AR content
        
    Returns:
        Public URL of the generated QR code
    """
    # Create QR code with the unique link
    unique_link = build_unique_link(unique_id)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(unique_link)
    qr.make(fit=True)
    
    # Generate QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Save QR code to storage
    qr_code_path = storage_path / "qr_code.png"
    
    # Convert PIL image to bytes and save asynchronously
    img_byte_arr = io.BytesIO()
    qr_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    async with aiofiles.open(qr_code_path, "wb") as f:
        await f.write(img_byte_arr.getvalue())
    
    # Return public URL
    return build_public_url(qr_code_path)


async def save_uploaded_file(upload_file, destination_path: Path) -> None:
    """Save an uploaded file to the destination path asynchronously.
    
    Args:
        upload_file: The uploaded file object
        destination_path: The destination path to save the file
    """
    # Ensure parent directory exists
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(destination_path, "wb") as f:
        while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
            await f.write(chunk)