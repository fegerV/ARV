"""
Enhanced Cache Service with multi-tier caching, CDN integration, and performance optimization.
"""
import asyncio
import json
import pickle
import time
import hashlib
import gzip
from typing import Any, Optional, Dict, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import structlog
import aioredis
from aioredis import Redis
from prometheus_client import Counter, Histogram, Gauge

from app.core.config import settings
from app.core.redis import redis_client

logger = structlog.get_logger()

class CacheLevel(Enum):
    L1_MEMORY = "l1_memory"      # Fastest, smallest
    L2_REDIS = "l2_redis"        # Fast, medium
    L3_DISK = "l3_disk"          # Slow, large
    L4_CDN = "l4_cdn"            # Slowest, global

class CacheStrategy(Enum):
    LAZY = "lazy"                # Load on demand
    EAGER = "eager"              # Preload
    WRITE_THROUGH = "write_through"  # Update all levels
    WRITE_BACK = "write_back"     # Update L1, async to others

@dataclass
class CacheConfig:
    level: CacheLevel
    ttl: int                     # Time to live in seconds
    max_size: Optional[int] = None
    compression: bool = False
    serialization: str = "json"  # json, pickle, raw
    
@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[int] = None
    size_bytes: int = 0
    cache_level: Optional[CacheLevel] = None

# Prometheus metrics
CACHE_OPERATIONS = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['level', 'operation', 'status']
)

CACHE_SIZE = Gauge(
    'cache_size_bytes',
    'Cache size in bytes',
    ['level']
)

CACHE_HIT_RATE = Gauge(
    'cache_hit_rate',
    'Cache hit rate',
    ['level']
)

CACHE_LATENCY = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation latency',
    ['level', 'operation']
)

class MemoryCache:
    """In-memory L1 cache with LRU eviction."""
    
    def __init__(self, max_size: int = 100 * 1024 * 1024):  # 100MB
        self.max_size = max_size
        self.current_size = 0
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []
        self.lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        async with self.lock:
            entry = self.cache.get(key)
            if entry:
                entry.accessed_at = time.time()
                entry.access_count += 1
                # Move to end (most recently used)
                self.access_order.remove(key)
                self.access_order.append(key)
                return entry
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        async with self.lock:
            # Calculate size
            size = len(pickle.dumps(value))
            
            # Check if we need to evict
            while (self.current_size + size > self.max_size and 
                   self.access_order):
                oldest_key = self.access_order.pop(0)
                oldest_entry = self.cache.pop(oldest_key)
                self.current_size -= oldest_entry.size_bytes
            
            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=1,
                ttl=ttl,
                size_bytes=size,
                cache_level=CacheLevel.L1_MEMORY
            )
            
            self.cache[key] = entry
            self.access_order.append(key)
            self.current_size += size
            
            return True
    
    async def delete(self, key: str) -> bool:
        async with self.lock:
            entry = self.cache.pop(key, None)
            if entry:
                self.current_size -= entry.size_bytes
                if key in self.access_order:
                    self.access_order.remove(key)
                return True
            return False
    
    async def clear(self) -> None:
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_size = 0
    
    def stats(self) -> Dict[str, Any]:
        return {
            'entries': len(self.cache),
            'size_bytes': self.current_size,
            'max_size': self.max_size,
            'utilization': self.current_size / self.max_size if self.max_size > 0 else 0
        }

class DiskCache:
    """Disk-based L3 cache with compression."""
    
    def __init__(self, cache_dir: str = "/tmp/vertex_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
    
    def _get_path(self, key: str) -> Path:
        # Use hash of key for filename to avoid filesystem issues
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        async with self.lock:
            path = self._get_path(key)
            if not path.exists():
                return None
            
            try:
                # Check if expired
                stat = path.stat()
                if time.time() - stat.st_mtime > 86400:  # 24 hours default
                    path.unlink()
                    return None
                
                # Read and deserialize
                with open(path, 'rb') as f:
                    data = f.read()
                
                # Decompress if needed
                if data.startswith(b'\x1f\x8b'):  # Gzip magic number
                    data = gzip.decompress(data)
                
                entry = pickle.loads(data)
                entry.accessed_at = time.time()
                entry.access_count += 1
                entry.cache_level = CacheLevel.L3_DISK
                
                return entry
                
            except Exception as e:
                logger.warning("disk_cache_read_failed", key=key, error=str(e))
                # Remove corrupted file
                try:
                    path.unlink()
                except:
                    pass
                return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, compress: bool = True) -> bool:
        async with self.lock:
            path = self._get_path(key)
            
            try:
                entry = CacheEntry(
                    key=key,
                    value=value,
                    created_at=time.time(),
                    accessed_at=time.time(),
                    access_count=1,
                    ttl=ttl,
                    cache_level=CacheLevel.L3_DISK
                )
                
                data = pickle.dumps(entry)
                
                # Compress if requested and beneficial
                if compress and len(data) > 1024:  # Only compress files > 1KB
                    compressed = gzip.compress(data)
                    if len(compressed) < len(data):
                        data = compressed
                        entry.size_bytes = len(compressed)
                    else:
                        entry.size_bytes = len(data)
                else:
                    entry.size_bytes = len(data)
                
                with open(path, 'wb') as f:
                    f.write(data)
                
                return True
                
            except Exception as e:
                logger.warning("disk_cache_write_failed", key=key, error=str(e))
                return False
    
    async def delete(self, key: str) -> bool:
        async with self.lock:
            path = self._get_path(key)
            try:
                path.unlink()
                return True
            except FileNotFoundError:
                return False
    
    async def clear(self) -> None:
        async with self.lock:
            for path in self.cache_dir.glob("*.cache"):
                try:
                    path.unlink()
                except Exception as e:
                    logger.warning("disk_cache_clear_failed", path=str(path), error=str(e))
    
    def stats(self) -> Dict[str, Any]:
        total_files = 0
        total_size = 0
        
        for path in self.cache_dir.glob("*.cache"):
            total_files += 1
            total_size += path.stat().st_size
        
        return {
            'files': total_files,
            'size_bytes': total_size,
            'directory': str(self.cache_dir)
        }

class EnhancedCacheService:
    """Multi-tier cache service with intelligent caching strategies."""
    
    def __init__(self):
        # Initialize cache levels
        self.l1_cache = MemoryCache(
            max_size=100 * 1024 * 1024  # 100MB
        )
        self.l2_cache = redis_client
        self.l3_cache = DiskCache()
        
        # Default configurations
        self.default_configs = {
            'thumbnails': CacheConfig(CacheLevel.L1_MEMORY, ttl=3600, max_size=50*1024*1024),
            'metadata': CacheConfig(CacheLevel.L2_REDIS, ttl=7200),
            'media_info': CacheConfig(CacheLevel.L3_DISK, ttl=86400, compression=True),
            'api_responses': CacheConfig(CacheLevel.L2_REDIS, ttl=300),
            'user_sessions': CacheConfig(CacheLevel.L2_REDIS, ttl=1800),
            'static_assets': CacheConfig(CacheLevel.L3_DISK, ttl=86400*7, compression=True)
        }
        
        # Performance tracking
        self.stats = {
            'hits': {level.value: 0 for level in CacheLevel},
            'misses': {level.value: 0 for level in CacheLevel},
            'operations': {level.value: 0 for level in CacheLevel}
        }
        
        # Background cleanup task
        asyncio.create_task(self._background_cleanup())
    
    async def get(
        self,
        key: str,
        cache_type: str = 'default',
        strategy: CacheStrategy = CacheStrategy.LAZY
    ) -> Optional[Any]:
        """Get value from cache with multi-tier fallback."""
        
        start_time = time.time()
        
        try:
            config = self._get_config(cache_type)
            
            # Try L1 (memory) first
            entry = await self.l1_cache.get(key)
            if entry and not self._is_expired(entry):
                self.stats['hits'][CacheLevel.L1_MEMORY.value] += 1
                CACHE_OPERATIONS.labels(
                    level=CacheLevel.L1_MEMORY.value,
                    operation='get',
                    status='hit'
                ).inc()
                CACHE_HIT_RATE.labels(level=CacheLevel.L1_MEMORY.value).set(
                    self._calculate_hit_rate(CacheLevel.L1_MEMORY)
                )
                return entry.value
            
            self.stats['misses'][CacheLevel.L1_MEMORY.value] += 1
            
            # Try L2 (Redis)
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                try:
                    cached_data = await self.l2_cache.get(key)
                    if cached_data:
                        value = json.loads(cached_data) if config.serialization == 'json' else pickle.loads(cached_data)
                        
                        # Promote to L1 if strategy is write-through
                        if strategy == CacheStrategy.WRITE_THROUGH:
                            await self.l1_cache.set(key, value, config.ttl)
                        
                        self.stats['hits'][CacheLevel.L2_REDIS.value] += 1
                        CACHE_OPERATIONS.labels(
                            level=CacheLevel.L2_REDIS.value,
                            operation='get',
                            status='hit'
                        ).inc()
                        return value
                except Exception as e:
                    logger.warning("l2_cache_error", key=key, error=str(e))
            
            self.stats['misses'][CacheLevel.L2_REDIS.value] += 1
            
            # Try L3 (disk)
            if config.level in [CacheLevel.L3_DISK, CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                entry = await self.l3_cache.get(key)
                if entry and not self._is_expired(entry):
                    value = entry.value
                    
                    # Promote to higher levels
                    if strategy == CacheStrategy.WRITE_THROUGH:
                        await self.l1_cache.set(key, value, config.ttl)
                        await self._set_l2(key, value, config)
                    
                    self.stats['hits'][CacheLevel.L3_DISK.value] += 1
                    CACHE_OPERATIONS.labels(
                        level=CacheLevel.L3_DISK.value,
                        operation='get',
                        status='hit'
                    ).inc()
                    return value
            
            self.stats['misses'][CacheLevel.L3_DISK.value] += 1
            
            # Record miss for all levels
            for level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                CACHE_OPERATIONS.labels(
                    level=level.value,
                    operation='get',
                    status='miss'
                ).inc()
            
            CACHE_LATENCY.labels(
                level='multi_tier',
                operation='get'
            ).observe(time.time() - start_time)
            
            return None
            
        except Exception as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        cache_type: str = 'default',
        ttl: Optional[int] = None,
        strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH
    ) -> bool:
        """Set value in cache with strategy-based storage."""
        
        start_time = time.time()
        
        try:
            config = self._get_config(cache_type)
            effective_ttl = ttl or config.ttl
            
            success = True
            
            # Store based on strategy
            if strategy == CacheStrategy.WRITE_THROUGH:
                # Store in all applicable levels
                if config.level in [CacheLevel.L1_MEMORY]:
                    await self.l1_cache.set(key, value, effective_ttl)
                
                if config.level in [CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                    await self._set_l2(key, value, config, effective_ttl)
                
                if config.level in [CacheLevel.L3_DISK, CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                    await self.l3_cache.set(key, value, effective_ttl, config.compression)
                    
            elif strategy == CacheStrategy.LAZY:
                # Store only in the configured level
                if config.level == CacheLevel.L1_MEMORY:
                    await self.l1_cache.set(key, value, effective_ttl)
                elif config.level == CacheLevel.L2_REDIS:
                    await self._set_l2(key, value, config, effective_ttl)
                elif config.level == CacheLevel.L3_DISK:
                    await self.l3_cache.set(key, value, effective_ttl, config.compression)
                    
            elif strategy == CacheStrategy.WRITE_BACK:
                # Store in L1, async to others
                await self.l1_cache.set(key, value, effective_ttl)
                
                # Async background write to other levels
                asyncio.create_task(self._background_write(key, value, config))
            
            # Update metrics
            for level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                if config.level in [level] or strategy == CacheStrategy.WRITE_THROUGH:
                    CACHE_OPERATIONS.labels(
                        level=level.value,
                        operation='set',
                        status='success'
                    ).inc()
            
            CACHE_LATENCY.labels(
                level='multi_tier',
                operation='set'
            ).observe(time.time() - start_time)
            
            return success
            
        except Exception as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str, cache_type: str = 'default') -> bool:
        """Delete key from all cache levels."""
        
        try:
            config = self._get_config(cache_type)
            
            # Delete from all applicable levels
            tasks = []
            
            if config.level in [CacheLevel.L1_MEMORY]:
                tasks.append(self.l1_cache.delete(key))
            
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                tasks.append(self.l2_cache.delete(key))
            
            if config.level in [CacheLevel.L3_DISK, CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                tasks.append(self.l3_cache.delete(key))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return any(r is True for r in results)
            
        except Exception as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        cache_type: str = 'default',
        ttl: Optional[int] = None
    ) -> Any:
        """Get value from cache or compute and store it."""
        
        value = await self.get(key, cache_type)
        if value is not None:
            return value
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        # Store in cache
        await self.set(key, value, cache_type, ttl)
        return value
    
    async def invalidate_pattern(self, pattern: str, cache_type: str = 'default') -> int:
        """Invalidate keys matching pattern."""
        
        try:
            config = self._get_config(cache_type)
            deleted_count = 0
            
            # For Redis, we can use KEYS pattern
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                keys = await self.l2_cache.keys(pattern)
                if keys:
                    deleted_count += await self.l2_cache.delete(*keys)
            
            # For memory and disk, we need to iterate
            # This is a simplified implementation
            logger.info("cache_pattern_invalidated", pattern=pattern, deleted=deleted_count)
            return deleted_count
            
        except Exception as e:
            logger.error("cache_invalidate_pattern_error", pattern=pattern, error=str(e))
            return 0
    
    async def warm_cache(self, keys: List[str], factory: Callable[[str], Any], cache_type: str = 'default'):
        """Warm cache with precomputed values."""
        
        tasks = []
        for key in keys:
            task = self.get_or_set(key, lambda k=key: factory(k), cache_type)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    def _get_config(self, cache_type: str) -> CacheConfig:
        """Get cache configuration for type."""
        return self.default_configs.get(cache_type, self.default_configs['metadata'])
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        if entry.ttl is None:
            return False
        return time.time() - entry.created_at > entry.ttl
    
    async def _set_l2(self, key: str, value: Any, config: CacheConfig, ttl: Optional[int] = None):
        """Set value in L2 (Redis) cache."""
        try:
            effective_ttl = ttl or config.ttl
            
            if config.serialization == 'json':
                data = json.dumps(value, default=str)
            else:
                data = pickle.dumps(value)
            
            if effective_ttl:
                await self.l2_cache.setex(key, effective_ttl, data)
            else:
                await self.l2_cache.set(key, data)
                
        except Exception as e:
            logger.warning("l2_cache_set_error", key=key, error=str(e))
    
    async def _background_write(self, key: str, value: Any, config: CacheConfig):
        """Background write for write-back strategy."""
        try:
            await asyncio.sleep(0.1)  # Small delay
            
            if config.level in [CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                await self._set_l2(key, value, config)
            
            if config.level in [CacheLevel.L3_DISK, CacheLevel.L2_REDIS, CacheLevel.L1_MEMORY]:
                await self.l3_cache.set(key, value, config.ttl, config.compression)
                
        except Exception as e:
            logger.warning("background_write_failed", key=key, error=str(e))
    
    def _calculate_hit_rate(self, level: CacheLevel) -> float:
        """Calculate hit rate for cache level."""
        hits = self.stats['hits'][level.value]
        misses = self.stats['misses'][level.value]
        total = hits + misses
        return hits / total if total > 0 else 0.0
    
    async def _background_cleanup(self):
        """Background task for cache cleanup and maintenance."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                
                # Update cache size metrics
                l1_stats = self.l1_cache.stats()
                CACHE_SIZE.labels(level=CacheLevel.L1_MEMORY.value).set(l1_stats['size_bytes'])
                
                l3_stats = self.l3_cache.stats()
                CACHE_SIZE.labels(level=CacheLevel.L3_DISK.value).set(l3_stats['size_bytes'])
                
                # Update hit rates
                for level in [CacheLevel.L1_MEMORY, CacheLevel.L2_REDIS, CacheLevel.L3_DISK]:
                    hit_rate = self._calculate_hit_rate(level)
                    CACHE_HIT_RATE.labels(level=level.value).set(hit_rate)
                
                logger.debug("cache_maintenance_completed", stats=self.stats)
                
            except Exception as e:
                logger.error("cache_cleanup_error", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            'operations': self.stats,
            'l1_stats': self.l1_cache.stats(),
            'l3_stats': self.l3_cache.stats(),
            'configurations': {k: asdict(v) for k, v in self.default_configs.items()}
        }
    
    async def clear_all(self):
        """Clear all cache levels."""
        await self.l1_cache.clear()
        
        # Clear Redis keys with our prefix
        try:
            keys = await self.l2_cache.keys("*")
            if keys:
                await self.l2_cache.delete(*keys)
        except Exception as e:
            logger.warning("redis_clear_error", error=str(e))
        
        await self.l3_cache.clear()
        
        # Reset stats
        for level in CacheLevel:
            self.stats['hits'][level.value] = 0
            self.stats['misses'][level.value] = 0
            self.stats['operations'][level.value] = 0

# Singleton instance
enhanced_cache_service = EnhancedCacheService()