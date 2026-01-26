"""
Video processing utilities for validation, metadata extraction, and ffprobe operations.
"""
import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
import structlog
from fastapi import UploadFile, HTTPException

logger = structlog.get_logger()

# Allowed video MIME types and extensions
ALLOWED_VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/webm", 
    "video/quicktime",  # .mov
    "video/x-msvideo",   # .avi
    "video/x-matroska",  # .mkv
}

ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mov",
    ".avi",
    ".mkv",
    ".m4v",
    ".3gp",
    ".flv",
    ".wmv",
}

MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB


def validate_video_file(upload_file: UploadFile) -> None:
    """
    Validate uploaded video file MIME type and extension.
    
    Args:
        upload_file: The uploaded file to validate
        
    Raises:
        HTTPException: If validation fails
    """
    # Check MIME type
    if upload_file.content_type and upload_file.content_type not in ALLOWED_VIDEO_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported MIME type: {upload_file.content_type}. "
                   f"Allowed types: {', '.join(sorted(ALLOWED_VIDEO_MIME_TYPES))}"
        )
    
    # Check file extension
    filename = upload_file.filename.lower() if upload_file.filename else ""
    if not any(filename.endswith(ext) for ext in ALLOWED_VIDEO_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {filename}. "
                   f"Allowed extensions: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"
        )


async def get_video_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract video metadata using ffprobe.
    
    Args:
        file_path: Path to the video file
        
    Returns:
        Dictionary containing video metadata
        
    Raises:
        RuntimeError: If ffprobe fails or file is not a valid video
    """
    log = logger.bind(file_path=file_path)
    
    def _parse_fps(value: Optional[str]) -> float:
        if not value:
            return 0.0
        parts = value.split("/")
        if len(parts) == 2:
            try:
                numerator = float(parts[0])
                denominator = float(parts[1])
                if denominator == 0:
                    return 0.0
                return numerator / denominator
            except ValueError:
                return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    try:
        # Run ffprobe to get video information
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            file_size = Path(file_path).stat().st_size
            log.warning("ffprobe_missing", error=str(exc))
            return {
                "duration": 0.0,
                "width": 0,
                "height": 0,
                "size_bytes": file_size,
                "mime_type": "unknown",
                "codec": "unknown",
                "fps": 0.0,
                "bit_rate": 0,
            }
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode()
            log.error("ffprobe_failed", error=error_msg)
            raise RuntimeError(f"ffprobe failed: {error_msg}")
        
        # Parse JSON output
        probe_data = json.loads(stdout.decode())
        
        # Extract video stream information
        video_stream = None
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break
        
        if not video_stream:
            raise RuntimeError("No video stream found in file")
        
        # Extract format information
        format_info = probe_data.get("format", {})
        
        # Get file size
        file_size = Path(file_path).stat().st_size
        
        # Extract relevant metadata
        metadata = {
            "duration": float(format_info.get("duration", 0)),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "size_bytes": file_size,
            "mime_type": format_info.get("format_name", "unknown"),
            "codec": video_stream.get("codec_name", "unknown"),
            "fps": _parse_fps(video_stream.get("r_frame_rate")),
            "bit_rate": int(format_info.get("bit_rate", 0)),
        }
        
        log.info(
            "video_metadata_extracted",
            duration=metadata["duration"],
            width=metadata["width"],
            height=metadata["height"],
            size_bytes=metadata["size_bytes"],
            codec=metadata["codec"]
        )
        
        return metadata
        
    except json.JSONDecodeError as e:
        log.error("ffprobe_json_parse_failed", error=str(e))
        raise RuntimeError(f"Failed to parse ffprobe output: {e}")
    except Exception as e:
        log.error("video_metadata_extraction_failed", error=str(e))
        raise RuntimeError(f"Failed to extract video metadata: {e}")


async def get_video_middle_frame_time(file_path: str) -> float:
    """
    Get the timestamp for the middle frame of a video.
    
    Args:
        file_path: Path to the video file
        
    Returns:
        Float representing the time in seconds for the middle frame
    """
    metadata = await get_video_metadata(file_path)
    duration = metadata.get("duration", 0)
    
    if duration <= 0:
        # Fallback to 1 second if duration detection fails
        return 1.0
    
    # Return middle timestamp (50% of duration)
    return duration / 2.0


async def save_uploaded_video(upload_file: UploadFile, destination_path: Path) -> None:
    """
    Save an uploaded video file to the destination path asynchronously.
    
    Args:
        upload_file: The uploaded file object
        destination_path: The destination path to save the file
        
    Raises:
        HTTPException: If file size exceeds limit or save fails
    """
    # Ensure parent directory exists
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check file size during upload
    total_size = 0
    
    try:
        with destination_path.open("wb") as f:
            while chunk := await upload_file.read(1024 * 1024):  # 1MB chunks
                total_size += len(chunk)
                if total_size > MAX_VIDEO_SIZE:
                    if destination_path.exists():
                        destination_path.unlink()
                    logger.error(
                        "video_upload_too_large",
                        max_size_mb=MAX_VIDEO_SIZE // (1024 * 1024),
                        size_bytes=total_size,
                        path=str(destination_path),
                    )
                    raise HTTPException(
                        status_code=413,
                        detail=f"Video file too large. Maximum size: {MAX_VIDEO_SIZE // (1024*1024)}MB"
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        # Clean up partial file on error
        if destination_path.exists():
            destination_path.unlink()
        logger.error("video_save_failed", error=str(exc), path=str(destination_path))
        raise HTTPException(status_code=500, detail=f"Failed to save video file: {str(exc)}")


def generate_video_filename(original_filename: str, video_id: Optional[int] = None) -> str:
    """
    Generate a standardized filename for uploaded videos.
    
    Args:
        original_filename: Original uploaded filename
        video_id: Optional video ID to include in filename
        
    Returns:
        Standardized filename with proper extension
    """
    # Extract original extension
    original_path = Path(original_filename.lower())
    extension = original_path.suffix
    
    # Ensure extension is allowed
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {extension}")
    
    # Generate base filename
    if video_id:
        base_name = f"video_{video_id}"
    else:
        base_name = original_path.stem.replace(" ", "_").replace("-", "_")
    
    return f"{base_name}{extension}"