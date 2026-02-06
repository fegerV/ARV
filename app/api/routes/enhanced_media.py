"""
Enhanced Media API routes with advanced validation, caching, and reliability.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import asyncio
from pathlib import Path

from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.video import Video
from app.services.enhanced_thumbnail_service import (
    enhanced_thumbnail_service, 
    ThumbnailConfig, 
    ThumbnailSize, 
    ThumbnailFormat,
    ValidationResult as ThumbnailValidationResult
)
from app.services.enhanced_validation_service import (
    enhanced_validation_service,
    ValidationLevel,
    FileConstraints,
    ValidationResult
)
from app.services.enhanced_cache_service import enhanced_cache_service
from app.services.reliability_service import (
    reliability_service,
    CircuitBreakerConfig,
    RetryConfig,
    reliable
)
from app.core.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v2/media", tags=["Enhanced Media"])

# Pydantic models
class ThumbnailRequest(BaseModel):
    file_path: str
    size: str = Field(default="medium", regex="^(small|medium|large|hero)$")
    format: str = Field(default="webp", regex="^(jpeg|webp|avif|png)$")
    quality: Optional[int] = Field(default=85, ge=1, le=100)
    force_regenerate: bool = False

class BatchThumbnailRequest(BaseModel):
    file_paths: List[str]
    sizes: List[str] = Field(default=["medium"], regex="^(small|medium|large|hero)$")
    formats: List[str] = Field(default=["webp"], regex="^(jpeg|webp|avif|png)$")
    quality: Optional[int] = Field(default=85, ge=1, le=100)
    force_regenerate: bool = False

class ValidationRequest(BaseModel):
    file_path: str
    file_type: str = Field(default="auto", regex="^(auto|image|video)$")
    validation_level: str = Field(default="standard", regex="^(basic|standard|comprehensive|paranoid)$")
    original_filename: Optional[str] = None

class BatchValidationRequest(BaseModel):
    file_paths: List[str]
    file_type: str = Field(default="auto", regex="^(auto|image|video)$")
    validation_level: str = Field(default="standard", regex="^(basic|standard|comprehensive|paranoid)$")

class MediaInfoResponse(BaseModel):
    file_path: str
    file_type: str
    validation_result: Dict[str, Any]
    thumbnail_info: Dict[str, Any]
    cache_status: Dict[str, Any]
    metadata: Dict[str, Any]

class SystemHealthResponse(BaseModel):
    status: str
    message: str
    services: Dict[str, Any]
    cache_stats: Dict[str, Any]
    reliability_stats: Dict[str, Any]
    timestamp: str

@router.post("/thumbnails/generate", response_model=Dict[str, Any])
@reliable(
    service_name="thumbnail_generation",
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=3, timeout=30),
    retry_config=RetryConfig(max_attempts=2)
)
async def generate_thumbnail(
    request: ThumbnailRequest,
    background_tasks: BackgroundTasks
):
    """Generate thumbnail with enhanced caching and validation."""
    
    try:
        # Parse size and format
        size_enum = ThumbnailSize(request.size.upper())
        format_enum = ThumbnailFormat(request.format.upper())
        
        # Create thumbnail config
        config = ThumbnailConfig(
            size=size_enum,
            format=format_enum,
            quality=request.quality or 85,
            optimize=True
        )
        
        # Check cache first
        cache_key = f"thumbnail_request:{hashlib.md5(str(request.dict()).encode()).hexdigest()}"
        cached_result = await enhanced_cache_service.get(cache_key, 'thumbnails')
        
        if cached_result and not request.force_regenerate:
            return {
                "status": "cached",
                "result": cached_result,
                "message": "Thumbnail retrieved from cache"
            }
        
        # Generate thumbnail
        result = await enhanced_thumbnail_service.generate_thumbnail(
            file_path=request.file_path,
            config=config,
            force_regenerate=request.force_regenerate
        )
        
        response_data = {
            "status": result.status,
            "thumbnail_url": result.thumbnail_url,
            "thumbnail_path": result.thumbnail_path,
            "config": {
                "size": config.size.size_name,
                "format": config.format.value,
                "quality": config.quality
            },
            "file_size": result.file_size,
            "generation_time": result.generation_time,
            "cache_hit": result.cache_hit
        }
        
        # Cache successful result
        if result.status == "ready":
            await enhanced_cache_service.set(
                cache_key,
                response_data,
                'thumbnails',
                ttl=3600  # 1 hour
            )
        
        return response_data
        
    except Exception as e:
        logger.error("thumbnail_generation_failed", file_path=request.file_path, error=str(e))
        raise HTTPException(status_code=500, detail=f"Thumbnail generation failed: {str(e)}")

@router.post("/thumbnails/batch", response_model=List[Dict[str, Any]])
async def generate_batch_thumbnails(
    request: BatchThumbnailRequest,
    background_tasks: BackgroundTasks
):
    """Generate multiple thumbnails concurrently."""
    
    try:
        # Create configurations for all requested sizes and formats
        configs = []
        for size_str in request.sizes:
            for format_str in request.formats:
                size_enum = ThumbnailSize(size_str.upper())
                format_enum = ThumbnailFormat(format_str.upper())
                
                configs.append(ThumbnailConfig(
                    size=size_enum,
                    format=format_enum,
                    quality=request.quality or 85,
                    optimize=True
                ))
        
        # Generate thumbnails for all files
        all_results = []
        
        for file_path in request.file_paths:
            try:
                results = await enhanced_thumbnail_service.generate_multiple_thumbnails(
                    file_path=file_path,
                    configs=configs,
                    force_regenerate=request.force_regenerate
                )
                
                file_results = {
                    "file_path": file_path,
                    "thumbnails": []
                }
                
                for result in results:
                    if result.status == "ready":
                        file_results["thumbnails"].append({
                            "size": result.config.size.size_name,
                            "format": result.config.format.value,
                            "url": result.thumbnail_url,
                            "path": result.thumbnail_path,
                            "size_bytes": result.file_size,
                            "generation_time": result.generation_time
                        })
                
                all_results.append(file_results)
                
            except Exception as e:
                logger.error("batch_thumbnail_failed", file_path=file_path, error=str(e))
                all_results.append({
                    "file_path": file_path,
                    "error": str(e),
                    "thumbnails": []
                })
        
        return all_results
        
    except Exception as e:
        logger.error("batch_thumbnail_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch thumbnail generation failed: {str(e)}")

@router.post("/validation/validate", response_model=Dict[str, Any])
@reliable(
    service_name="file_validation",
    circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5, timeout=60),
    retry_config=RetryConfig(max_attempts=1)  # No retry for validation
)
async def validate_file(request: ValidationRequest):
    """Validate file with comprehensive security scanning."""
    
    try:
        # Parse validation level
        level_enum = ValidationLevel(request.validation_level.upper())
        
        # Check cache first
        cache_key = f"validation:{hashlib.md5(str(request.dict()).encode()).hexdigest()}"
        cached_result = await enhanced_cache_service.get(cache_key, 'validation')
        
        if cached_result:
            return {
                "status": "cached",
                "result": cached_result,
                "message": "Validation result retrieved from cache"
            }
        
        # Perform validation
        result = await enhanced_validation_service.validate_file(
            file_path=request.file_path,
            file_type=request.file_type,
            validation_level=level_enum,
            original_filename=request.original_filename
        )
        
        # Convert to dict for response
        response_data = {
            "is_valid": result.is_valid,
            "threat_level": result.threat_level.value,
            "errors": result.errors,
            "warnings": result.warnings,
            "metadata": result.metadata,
            "security_info": result.security_info,
            "file_info": result.file_info,
            "validation_time": result.validation_time,
            "validation_level": result.validation_level.value
        }
        
        # Cache validation result (shorter TTL for security)
        await enhanced_cache_service.set(
            cache_key,
            response_data,
            'validation',
            ttl=300  # 5 minutes
        )
        
        return response_data
        
    except Exception as e:
        logger.error("file_validation_failed", file_path=request.file_path, error=str(e))
        raise HTTPException(status_code=500, detail=f"File validation failed: {str(e)}")

@router.post("/validation/batch", response_model=List[Dict[str, Any]])
async def validate_batch_files(request: BatchValidationRequest):
    """Validate multiple files concurrently."""
    
    try:
        level_enum = ValidationLevel(request.validation_level.upper())
        
        # Perform batch validation
        results = await enhanced_validation_service.batch_validate(
            file_paths=request.file_paths,
            validation_level=level_enum
        )
        
        # Convert to response format
        response_data = []
        for i, result in enumerate(results):
            response_data.append({
                "file_path": request.file_paths[i],
                "is_valid": result.is_valid,
                "threat_level": result.threat_level.value,
                "errors": result.errors,
                "warnings": result.warnings,
                "metadata": result.metadata,
                "security_info": result.security_info,
                "file_info": result.file_info,
                "validation_time": result.validation_time,
                "validation_level": result.validation_level.value
            })
        
        return response_data
        
    except Exception as e:
        logger.error("batch_validation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Batch validation failed: {str(e)}")

@router.get("/info/{file_path:path}", response_model=MediaInfoResponse)
async def get_media_info(file_path: str):
    """Get comprehensive media information."""
    
    try:
        # Get thumbnail info
        thumbnail_info = await enhanced_thumbnail_service.get_thumbnail_info(file_path)
        
        # Get validation summary (basic level for performance)
        validation_result = await enhanced_validation_service.validate_file(
            file_path=file_path,
            validation_level=ValidationLevel.BASIC
        )
        
        # Get cache status
        cache_stats = enhanced_cache_service.get_stats()
        
        # Combine metadata
        metadata = {
            "validation": validation_result.metadata,
            "thumbnails": thumbnail_info
        }
        
        return MediaInfoResponse(
            file_path=file_path,
            file_type="unknown",  # Could be detected
            validation_result={
                "is_valid": validation_result.is_valid,
                "threat_level": validation_result.threat_level.value,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            },
            thumbnail_info=thumbnail_info,
            cache_status={
                "cache_available": cache_stats['l1_stats']['entries'] > 0,
                "memory_entries": cache_stats['l1_stats']['entries'],
                "disk_files": cache_stats['l3_stats']['files']
            },
            metadata=metadata
        )
        
    except Exception as e:
        logger.error("media_info_failed", file_path=file_path, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get media info: {str(e)}")

@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Cache pattern to clear"),
    cache_type: Optional[str] = Query(None, description="Cache type to clear")
):
    """Clear cache entries."""
    
    try:
        if pattern:
            deleted_count = await enhanced_cache_service.invalidate_pattern(pattern, cache_type or 'default')
            return {
                "status": "success",
                "message": f"Cache pattern cleared",
                "deleted_count": deleted_count,
                "pattern": pattern
            }
        else:
            await enhanced_cache_service.clear_all()
            return {
                "status": "success",
                "message": "All cache cleared"
            }
            
    except Exception as e:
        logger.error("cache_clear_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/cache/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """Get comprehensive cache statistics."""
    
    try:
        return enhanced_cache_service.get_stats()
    except Exception as e:
        logger.error("cache_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health():
    """Get comprehensive system health status."""
    
    try:
        # Get health status from reliability service
        health_status = await reliability_service.health_checker.get_overall_health()
        
        # Get cache stats
        cache_stats = enhanced_cache_service.get_stats()
        
        # Get reliability stats
        reliability_stats = await reliability_service.get_reliability_stats()
        
        return SystemHealthResponse(
            status=health_status['status'],
            message=health_status['message'],
            services=health_status['checks'],
            cache_stats=cache_stats,
            reliability_stats=reliability_stats,
            timestamp=health_status['timestamp']
        )
        
    except Exception as e:
        logger.error("system_health_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system health: {str(e)}")

@router.post("/ar-content/{content_id}/enhanced-thumbnails")
async def generate_ar_content_thumbnails(
    content_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate enhanced thumbnails for AR content (photo and videos)."""
    
    try:
        # Parse UUID
        try:
            content_uuid = uuid.UUID(content_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content ID format")
        
        # Get AR content by unique_id (string), not by UUID object
        stmt = select(ARContent).where(ARContent.unique_id == content_id)
        result = await db.execute(stmt)
        ar_content = result.scalar_one_or_none()
        
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        
        # Get associated videos using the actual AR content ID
        videos_stmt = select(Video).where(Video.ar_content_id == ar_content.id)
        videos_result = await db.execute(videos_stmt)
        videos = videos_result.scalars().all()
        
        # Files to process
        files_to_process = []
        
        # Add photo if exists
        if ar_content.photo_path:
            files_to_process.append({
                "path": ar_content.photo_path,
                "type": "image",
                "name": "photo"
            })
        
        # Add videos
        for video in videos:
            if video.video_path:
                files_to_process.append({
                    "path": video.video_path,
                    "type": "video",
                    "name": f"video_{video.id}",
                    "video_id": video.id
                })
        
        if not files_to_process:
            return {
                "status": "no_files",
                "message": "No media files found for this AR content"
            }
        
        # Generate thumbnails for all files
        results = []
        
        for file_info in files_to_process:
            try:
                # Generate multiple sizes
                configs = [
                    ThumbnailConfig(ThumbnailSize.SMALL, ThumbnailFormat.WEBP, 80),
                    ThumbnailConfig(ThumbnailSize.MEDIUM, ThumbnailFormat.WEBP, 85),
                    ThumbnailConfig(ThumbnailSize.LARGE, ThumbnailFormat.WEBP, 90),
                ]
                
                thumbnail_results = await enhanced_thumbnail_service.generate_multiple_thumbnails(
                    file_path=file_info["path"],
                    configs=configs,
                    company_id=ar_content.company_id
                )
                
                # Update database with new thumbnails
                if file_info["type"] == "image" and ar_content:
                    # Update AR content thumbnail URL
                    for thumb_result in thumbnail_results:
                        if thumb_result.status == "ready" and thumb_result.config.size == ThumbnailSize.MEDIUM:
                            ar_content.thumbnail_url = thumb_result.thumbnail_url
                            break
                
                elif file_info["type"] == "video" and "video_id" in file_info:
                    # Update video thumbnail URLs
                    video = next((v for v in videos if v.id == file_info["video_id"]), None)
                    if video:
                        for thumb_result in thumbnail_results:
                            if thumb_result.status == "ready":
                                if thumb_result.config.size == ThumbnailSize.MEDIUM:
                                    video.thumbnail_url = thumb_result.thumbnail_url
                                elif thumb_result.config.size == ThumbnailSize.SMALL:
                                    video.preview_url = thumb_result.thumbnail_url
                
                results.append({
                    "file": file_info["name"],
                    "type": file_info["type"],
                    "status": "success",
                    "thumbnails": [
                        {
                            "size": tr.config.size.size_name,
                            "format": tr.config.format.value,
                            "url": tr.thumbnail_url,
                            "path": tr.thumbnail_path
                        }
                        for tr in thumbnail_results if tr.status == "ready"
                    ]
                })
                
            except Exception as e:
                logger.error("ar_content_thumbnail_failed", 
                           content_id=content_id, 
                           file=file_info["name"], 
                           error=str(e))
                results.append({
                    "file": file_info["name"],
                    "type": file_info["type"],
                    "status": "failed",
                    "error": str(e)
                })
        
        # Commit database changes
        await db.commit()
        
        return {
            "status": "completed",
            "content_id": content_id,
            "results": results,
            "processed_files": len(files_to_process),
            "successful_files": len([r for r in results if r["status"] == "success"])
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("ar_content_thumbnails_failed", content_id=content_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate AR content thumbnails: {str(e)}")

@router.get("/stats/summary")
async def get_media_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive media statistics."""
    
    try:
        # Get counts from database
        ar_content_count = await db.scalar(select(func.count(ARContent.id)))
        video_count = await db.scalar(select(func.count(Video.id)))
        
        # Get cache statistics
        cache_stats = enhanced_cache_service.get_stats()
        
        # Get reliability statistics
        reliability_stats = await reliability_service.get_reliability_stats()
        
        return {
            "database": {
                "ar_content_count": ar_content_count,
                "video_count": video_count
            },
            "cache": cache_stats,
            "reliability": reliability_stats,
            "system": {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": time.time() - start_time if 'start_time' in globals() else 0
            }
        }
        
    except Exception as e:
        logger.error("media_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get media stats: {str(e)}")

# Import required modules
import hashlib
from sqlalchemy import func
from datetime import datetime

# Track service start time
start_time = time.time()