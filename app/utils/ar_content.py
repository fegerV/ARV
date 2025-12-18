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
import re

from app.core.config import settings
from app.core.storage import get_storage_provider_instance


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
    """Convert a storage path to a public URL using the storage provider.
    
    Args:
        storage_path: The absolute storage path
        
    Returns:
        Public URL for accessing the file
    """
    storage_provider = get_storage_provider_instance()
    
    # Convert absolute path to relative path
    base_path = Path(settings.LOCAL_STORAGE_PATH)
    try:
        relative_path = storage_path.relative_to(base_path)
        return storage_provider.get_public_url(str(relative_path))
    except ValueError:
        # If path is not under base_path, fall back to simple URL building
        return f"/storage/{storage_path.name}"


def build_unique_link(unique_id: uuid.UUID) -> str:
    """Build the unique public link for AR content.
    
    Args:
        unique_id: The unique UUID for the AR content
        
    Returns:
        Public link URL
    """
    return f"/view/{unique_id}"


async def generate_qr_code(unique_id: uuid.UUID, storage_path: Path) -> str:
    """Generate QR code for AR content and save it to storage.
    
    Args:
        unique_id: The unique UUID for the AR content
        storage_path: The storage directory path for the AR content
        
    Returns:
        Public URL of the generated QR code
    """
    # Create QR code with the full public URL (so the QR works outside of current domain context)
    unique_link = build_unique_link(unique_id)
    unique_url = f"{settings.PUBLIC_URL.rstrip('/')}{unique_link}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(unique_url)
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


def validate_email_format(email: str) -> bool:
    """Validate email format using regex.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Validate file extension against allowed extensions.
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: List of allowed extensions (without dots)
        
    Returns:
        True if extension is allowed, False otherwise
    """
    ext = Path(filename).suffix.lower()[1:]  # Remove the dot
    return ext in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """Validate file size against maximum allowed size.
    
    Args:
        file_size: Size of the file in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if file size is within limits, False otherwise
    """
    return file_size <= max_size


async def generate_thumbnail(image_path: Path, thumbnail_path: Path, size=(200, 200)) -> None:
    """Generate a thumbnail for an image.
    
    Args:
        image_path: Path to the original image
        thumbnail_path: Path where the thumbnail will be saved
        size: Tuple of (width, height) for the thumbnail
    """
    # Open the original image
    with Image.open(image_path) as img:
        # Create thumbnail maintaining aspect ratio
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Create a blank image with the exact size and paste the thumbnail centered
        thumb = Image.new('RGB', size, (255, 255, 255))  # White background
        offset = ((size[0] - img.size[0]) // 2, (size[1] - img.size[1]) // 2)
        thumb.paste(img, offset)
        
        # Save the thumbnail
        thumb.save(thumbnail_path, optimize=True, quality=85)