"""
AR Content utilities for storage paths and QR code generation.
"""
from pathlib import Path
from typing import Optional
import qrcode
from PIL import Image
import io
import aiofiles
import re

from app.core.config import settings
from app.core.storage import get_storage_provider_instance
from app.utils.slug_utils import generate_slug


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """Convert name to filesystem-safe slug.
    
    Args:
        name: Original name to sanitize
        max_length: Maximum length of the resulting slug
        
    Returns:
        Sanitized filename-safe string
    """
    if not name:
        return "unnamed"
    
    # Replace spaces with underscores
    name = name.replace(' ', '_')
    
    # Remove or replace problematic characters for Windows/Linux filesystems
    # Windows: < > : " / \ | ? *
    # Linux: / (and null byte, but we handle that separately)
    name = re.sub(r'[<>:"/\\|?*\x00]', '', name)
    
    # Remove multiple underscores and dots
    name = re.sub(r'[_.]+', '_', name)
    
    # Remove leading/trailing dots and underscores
    name = name.strip('._')
    
    # Limit length
    if len(name) > max_length:
        name = name[:max_length]
    
    # If empty after sanitization, use default
    if not name:
        return "unnamed"
    
    return name


def build_ar_content_storage_path(
    company_id: int, 
    project_id: int, 
    order_number: str,
    company_name: Optional[str] = None,
    project_name: Optional[str] = None
) -> Path:
    """Build the storage path for AR content.
    
    Structure: {STORAGE_BASE_PATH}/VertexAR/{project_slug}/{order_number}
    
    Uses transliterated slug for project name to avoid Cyrillic issues in file paths.
    
    Args:
        company_id: The company ID (not used in path)
        project_id: The project ID
        order_number: The order number for the AR content
        company_name: Optional company name (not used in path)
        project_name: Optional project name (will be transliterated and sanitized)
        
    Returns:
        Path object for the AR content storage directory
    """
    # Base path
    base_path = Path(settings.STORAGE_BASE_PATH) / "VertexAR"
    
    # Build project folder: use transliterated slug instead of raw name
    if project_name:
        # Use generate_slug which includes transliteration for Cyrillic
        project_folder = generate_slug(project_name)
        # Fallback to sanitize_filename if slug is empty
        if not project_folder:
            project_folder = sanitize_filename(project_name)
    else:
        project_folder = f"Project_{project_id}"
    
    # Build order folder: {order_number}
    order_folder = sanitize_filename(order_number, max_length=50)
    
    return base_path / project_folder / order_folder


async def get_ar_content_storage_path(ar_content, db = None) -> Path:
    """Get storage path for AR content.
    
    Builds path using company and project names.
    
    Args:
        ar_content: ARContent model instance
        db: Optional database session to load relations if needed
        
    Returns:
        Path object for the AR content storage directory
    """
    # Build new path using company and project names
    company_name = None
    project_name = None
    
    # Try to get names from loaded relations
    if hasattr(ar_content, 'company') and ar_content.company:
        company_name = ar_content.company.name
    if hasattr(ar_content, 'project') and ar_content.project:
        project_name = ar_content.project.name
    
    # If relations not loaded and db provided, load them
    if db and (not company_name or not project_name):
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from app.models.ar_content import ARContent
        stmt = select(ARContent).options(
            selectinload(ARContent.company),
            selectinload(ARContent.project)
        ).where(ARContent.id == ar_content.id)
        result = await db.execute(stmt)
        ar_content_loaded = result.scalar_one()
        if not company_name and ar_content_loaded.company:
            company_name = ar_content_loaded.company.name
        if not project_name and ar_content_loaded.project:
            project_name = ar_content_loaded.project.name
    
    # Build new path
    return build_ar_content_storage_path(
        company_id=ar_content.company_id,
        project_id=ar_content.project_id,
        order_number=ar_content.order_number,
        company_name=company_name,
        project_name=project_name
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
    base_path = Path(settings.STORAGE_BASE_PATH)
    
    try:
        relative_path = storage_path.relative_to(base_path)
        relative_path_str = str(relative_path).replace('\\', '/')
        return storage_provider.get_public_url(relative_path_str)
    except ValueError:
        # If path is not under base_path, extract relative path from VertexAR
        path_str = str(storage_path).replace('\\', '/')
        if 'VertexAR' in path_str:
            vertexar_index = path_str.find('VertexAR')
            relative_path_str = path_str[vertexar_index:]
            relative_path_str = relative_path_str.replace('\\', '/')
            return storage_provider.get_public_url(relative_path_str)
        
        # Fallback: use just the filename
        return f"/storage/{storage_path.name}"


def build_unique_link(unique_id: str) -> str:
    """Build the unique public link for AR content.
    
    Args:
        unique_id: The unique UUID for the AR content
        
    Returns:
        Public link URL
    """
    return f"/view/{unique_id}"


async def generate_qr_code(unique_id: str, storage_path: Path) -> str:
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