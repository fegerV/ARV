"""
Enhanced Thumbnail Service with multiple sizes, caching, and progressive loading.
"""
import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from io import BytesIO

import structlog
from PIL import Image, ImageOps
import aioredis
from prometheus_client import Counter, Histogram, Gauge

from app.core.config import settings
from app.core.redis import redis_client

logger = structlog.get_logger()

# Thumbnail sizes configuration
class ThumbnailSize(Enum):
    SMALL = ("small", (150, 112))     # 4:3 ratio for lists
    MEDIUM = ("medium", (320, 240))   # Current standard
    LARGE = ("large", (640, 480))     # For lightbox
    HERO = ("hero", (1280, 720))      # For hero sections

    def __init__(self, name: str, dimensions: Tuple[int, int]):
        self.size_name = name
        self.width, self.height = dimensions

# Supported formats
class ThumbnailFormat(Enum):
    JPEG = "jpeg"
    WEBP = "webp"
    AVIF = "avif"
    PNG = "png"

@dataclass
class ThumbnailConfig:
    size: ThumbnailSize
    format: ThumbnailFormat
    quality: int = 85
    optimize: bool = True
    
    @property
    def file_extension(self) -> str:
        return f".{self.format.value}"

@dataclass
class ValidationResult:
    is_valid: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    file_hash: Optional[str] = None

@dataclass
class ThumbnailResult:
    status: str
    thumbnail_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    config: Optional[ThumbnailConfig] = None
    file_size: Optional[int] = None
    generation_time: Optional[float] = None
    cache_hit: bool = False

# Prometheus metrics
THUMBNAIL_GENERATION_COUNT = Counter(
    'enhanced_thumbnail_generation_total',
    'Total thumbnail generation attempts',
    ['size', 'format', 'status', 'cache_hit']
)

THUMBNAIL_GENERATION_DURATION = Histogram(
    'enhanced_thumbnail_generation_duration_seconds',
    'Time spent generating thumbnails',
    ['size', 'format']
)

THUMBNAIL_CACHE_SIZE = Gauge(
    'enhanced_thumbnail_cache_size',
    'Number of thumbnails cached'
)

THUMBNAIL_FILE_SIZE = Histogram(
    'enhanced_thumbnail_file_size_bytes',
    'Generated thumbnail file sizes',
    ['size', 'format']
)

class EnhancedThumbnailService:
    """Enhanced thumbnail service with caching and progressive loading."""
    
    def __init__(self):
        self.default_configs = [
            ThumbnailConfig(ThumbnailSize.SMALL, ThumbnailFormat.WEBP, 80),
            ThumbnailConfig(ThumbnailSize.MEDIUM, ThumbnailFormat.WEBP, 85),
            ThumbnailConfig(ThumbnailSize.LARGE, ThumbnailFormat.JPEG, 90),
        ]
        self.cache_ttl = 86400 * 30  # 30 days
        self.max_file_size = 50 * 1024 * 1024  # 50MB for source files
        
    async def get_file_hash(self, file_path: str) -> str:
        """Generate SHA-256 hash of file for cache key."""
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("file_hash_calculation_failed", file_path=file_path, error=str(e))
            raise
    
    def get_cache_key(self, file_hash: str, config: ThumbnailConfig) -> str:
        """Generate cache key for thumbnail."""
        return f"thumb:{config.size.size_name}:{config.format.value}:{file_hash}"
    
    async def get_cached_thumbnail(self, file_hash: str, config: ThumbnailConfig) -> Optional[ThumbnailResult]:
        """Get thumbnail from Redis cache."""
        try:
            cache_key = self.get_cache_key(file_hash, config)
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return ThumbnailResult(
                    status="ready",
                    thumbnail_path=data.get("thumbnail_path"),
                    thumbnail_url=data.get("thumbnail_url"),
                    config=config,
                    file_size=data.get("file_size"),
                    cache_hit=True
                )
        except Exception as e:
            logger.warning("cache_retrieval_failed", cache_key=cache_key, error=str(e))
        
        return None
    
    async def cache_thumbnail(self, file_hash: str, config: ThumbnailConfig, result: ThumbnailResult) -> None:
        """Cache thumbnail result in Redis."""
        try:
            cache_key = self.get_cache_key(file_hash, config)
            cache_data = {
                "thumbnail_path": result.thumbnail_path,
                "thumbnail_url": result.thumbnail_url,
                "file_size": result.file_size,
                "generated_at": time.time()
            }
            
            await redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_data)
            )
            
            # Update cache size gauge
            THUMBNAIL_CACHE_SIZE.inc()
            
        except Exception as e:
            logger.warning("cache_storage_failed", cache_key=cache_key, error=str(e))
    
    async def validate_image_file(self, file_path: str) -> ValidationResult:
        """Validate image file integrity and metadata."""
        try:
            path = Path(file_path)
            if not path.exists():
                return ValidationResult(False, "File does not exist")
            
            # Check file size
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                return ValidationResult(False, f"File too large: {file_size} bytes")
            
            # Validate image integrity
            with Image.open(file_path) as img:
                # Get image metadata
                metadata = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "has_transparency": img.mode in ('RGBA', 'LA', 'P'),
                    "file_size": file_size
                }
                
                # Try to load the image to verify integrity
                img.verify()
                
                # Reopen for metadata (verify() closes the file)
                with Image.open(file_path) as img:
                    if hasattr(img, 'getexif'):
                        exif = img.getexif()
                        if exif:
                            metadata["exif"] = dict(exif)
            
            file_hash = await self.get_file_hash(file_path)
            return ValidationResult(True, metadata=metadata, file_hash=file_hash)
            
        except Exception as e:
            return ValidationResult(False, f"Image validation failed: {str(e)}")
    
    async def generate_thumbnail(
        self,
        file_path: str,
        config: Optional[ThumbnailConfig] = None,
        provider=None,
        company_id: Optional[int] = None,
        force_regenerate: bool = False
    ) -> ThumbnailResult:
        """
        Generate thumbnail with caching and progressive loading support.
        
        Args:
            file_path: Path to source image
            config: Thumbnail configuration
            provider: Storage provider for cloud storage
            company_id: Company ID for storage path
            force_regenerate: Skip cache and regenerate
            
        Returns:
            ThumbnailResult with generation details
        """
        start_time = time.time()
        
        # Use default config if none provided
        if config is None:
            config = self.default_configs[1]  # Medium WEBP
        
        log = logger.bind(
            file_path=file_path,
            size=config.size.size_name,
            format=config.format.value,
            company_id=company_id
        )
        
        try:
            # Validate source file
            validation = await self.validate_image_file(file_path)
            if not validation.is_valid:
                return ThumbnailResult(
                    status="failed",
                    config=config,
                    generation_time=time.time() - start_time
                )
            
            file_hash = validation.file_hash
            
            # Check cache first (unless forced)
            if not force_regenerate:
                cached_result = await self.get_cached_thumbnail(file_hash, config)
                if cached_result:
                    THUMBNAIL_GENERATION_COUNT.labels(
                        size=config.size.size_name,
                        format=config.format.value,
                        status='success',
                        cache_hit='true'
                    ).inc()
                    return cached_result
            
            log.info("thumbnail_generation_started")
            
            # Generate thumbnail in memory
            thumbnail_data = await self._generate_thumbnail_in_memory(
                file_path, config, validation.metadata
            )
            
            # Generate filename
            source_filename = Path(file_path).stem
            thumbnail_name = f"{source_filename}_{config.size.size_name}{config.file_extension}"
            
            # Store thumbnail (local or cloud)
            if provider:
                storage_path = f"thumbnails/{company_id}/{thumbnail_name}" if company_id else f"thumbnails/{thumbnail_name}"
                thumbnail_url = await self._save_to_cloud_storage(
                    thumbnail_data, provider, storage_path, config
                )
                thumbnail_path = storage_path
            else:
                # Local storage
                output_dir = Path(settings.MEDIA_ROOT) / "thumbnails"
                output_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_path = str(output_dir / thumbnail_name)
                
                with open(thumbnail_path, 'wb') as f:
                    f.write(thumbnail_data)
                
                thumbnail_url = f"/storage/thumbnails/{thumbnail_name}"
            
            # Create result
            result = ThumbnailResult(
                status="ready",
                thumbnail_path=thumbnail_path,
                thumbnail_url=thumbnail_url,
                config=config,
                file_size=len(thumbnail_data),
                generation_time=time.time() - start_time,
                cache_hit=False
            )
            
            # Cache the result
            await self.cache_thumbnail(file_hash, config, result)
            
            # Record metrics
            THUMBNAIL_GENERATION_COUNT.labels(
                size=config.size.size_name,
                format=config.format.value,
                status='success',
                cache_hit='false'
            ).inc()
            
            THUMBNAIL_GENERATION_DURATION.labels(
                size=config.size.size_name,
                format=config.format.value
            ).observe(result.generation_time)
            
            THUMBNAIL_FILE_SIZE.labels(
                size=config.size.size_name,
                format=config.format.value
            ).observe(result.file_size)
            
            log.info(
                "thumbnail_generation_success",
                thumbnail_url=thumbnail_url,
                file_size=result.file_size,
                generation_time=result.generation_time
            )
            
            return result
            
        except Exception as e:
            # Record failure metrics
            THUMBNAIL_GENERATION_COUNT.labels(
                size=config.size.size_name,
                format=config.format.value,
                status='failed',
                cache_hit='false'
            ).inc()
            
            log.error("thumbnail_generation_failed", error=str(e), exc_info=True)
            return ThumbnailResult(
                status="failed",
                config=config,
                generation_time=time.time() - start_time
            )
    
    async def _generate_thumbnail_in_memory(
        self,
        file_path: str,
        config: ThumbnailConfig,
        source_metadata: Dict[str, Any]
    ) -> bytes:
        """Generate thumbnail in memory using PIL."""
        
        with Image.open(file_path) as img:
            # Convert to RGB if needed (for JPEG)
            if config.format == ThumbnailFormat.JPEG and img.mode in ('RGBA', 'LA', 'P'):
                # Create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode in ('RGBA', 'LA', 'P') and config.format != ThumbnailFormat.PNG:
                img = img.convert('RGB')
            
            # Calculate thumbnail size maintaining aspect ratio
            target_width, target_height = config.size.width, config.size.height
            
            # Use smart resize for better quality
            img = ImageOps.contain(img, (target_width, target_height), Image.Resampling.LANCZOS)
            
            # Save to bytes buffer
            buffer = BytesIO()
            
            save_kwargs = {
                'format': config.format.value.upper(),
                'optimize': config.optimize
            }
            
            if config.format in [ThumbnailFormat.JPEG, ThumbnailFormat.WEBP]:
                save_kwargs['quality'] = config.quality
            
            img.save(buffer, **save_kwargs)
            return buffer.getvalue()
    
    async def _save_to_cloud_storage(
        self,
        thumbnail_data: bytes,
        provider,
        storage_path: str,
        config: ThumbnailConfig
    ) -> str:
        """Save thumbnail to cloud storage."""
        import tempfile
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(thumbnail_data)
            temp_path = tmp_file.name
        
        try:
            content_type = f"image/{config.format.value}"
            url = await provider.upload_file(
                temp_path,
                storage_path,
                content_type
            )
            return url
        finally:
            # Clean up temporary file
            import os
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    async def generate_multiple_thumbnails(
        self,
        file_path: str,
        configs: Optional[List[ThumbnailConfig]] = None,
        provider=None,
        company_id: Optional[int] = None,
        force_regenerate: bool = False
    ) -> List[ThumbnailResult]:
        """Generate multiple thumbnails with different configurations."""
        
        if configs is None:
            configs = self.default_configs
        
        # Generate all thumbnails concurrently
        tasks = [
            self.generate_thumbnail(
                file_path=file_path,
                config=config,
                provider=provider,
                company_id=company_id,
                force_regenerate=force_regenerate
            )
            for config in configs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ThumbnailResult(
                    status="failed",
                    config=configs[i],
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def get_thumbnail_info(self, file_path: str) -> Dict[str, Any]:
        """Get information about available thumbnails for a file."""
        try:
            file_hash = await self.get_file_hash(file_path)
            
            info = {
                "file_hash": file_hash,
                "available_thumbnails": [],
                "cache_status": {}
            }
            
            # Check all default configurations
            for config in self.default_configs:
                cache_key = self.get_cache_key(file_hash, config)
                cached = await redis_client.exists(cache_key)
                
                thumbnail_info = {
                    "size": config.size.size_name,
                    "format": config.format.value,
                    "dimensions": (config.size.width, config.size.height),
                    "cached": bool(cached)
                }
                
                info["available_thumbnails"].append(thumbnail_info)
                info["cache_status"][config.size.size_name] = "cached" if cached else "not_cached"
            
            return info
            
        except Exception as e:
            logger.error("thumbnail_info_failed", file_path=file_path, error=str(e))
            return {"error": str(e)}
    
    async def clear_cache(self, file_path: Optional[str] = None) -> int:
        """Clear cache for specific file or all thumbnails."""
        try:
            if file_path:
                # Clear cache for specific file
                file_hash = await self.get_file_hash(file_path)
                keys_deleted = 0
                
                for config in self.default_configs:
                    cache_key = self.get_cache_key(file_hash, config)
                    deleted = await redis_client.delete(cache_key)
                    keys_deleted += deleted
                
                logger.info("cache_cleared_for_file", file_path=file_path, keys_deleted=keys_deleted)
                return keys_deleted
            else:
                # Clear all thumbnail cache
                pattern = "thumb:*"
                keys = await redis_client.keys(pattern)
                if keys:
                    deleted = await redis_client.delete(*keys)
                    logger.info("all_cache_cleared", keys_deleted=deleted)
                    return deleted
                return 0
                
        except Exception as e:
            logger.error("cache_clear_failed", file_path=file_path, error=str(e))
            return 0

# Singleton instance
enhanced_thumbnail_service = EnhancedThumbnailService()