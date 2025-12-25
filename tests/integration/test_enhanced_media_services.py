"""
Comprehensive tests for enhanced media services.
"""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import json
import time
from io import BytesIO
from PIL import Image
import cv2
import numpy as np

from app.services.enhanced_thumbnail_service import (
    EnhancedThumbnailService,
    ThumbnailConfig,
    ThumbnailSize,
    ThumbnailFormat,
    ValidationResult as ThumbnailValidationResult
)
from app.services.enhanced_validation_service import (
    EnhancedValidationService,
    ValidationLevel,
    ThreatLevel,
    FileConstraints
)
from app.services.enhanced_cache_service import (
    EnhancedCacheService,
    CacheLevel,
    CacheStrategy
)
from app.services.reliability_service import (
    ReliabilityService,
    CircuitBreakerConfig,
    RetryConfig,
    CircuitBreakerOpenError
)


class TestEnhancedThumbnailService:
    """Test cases for EnhancedThumbnailService."""
    
    @pytest.fixture
    def service(self):
        return EnhancedThumbnailService()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        img = Image.new('RGB', (800, 600), color='red')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f.name, 'JPEG')
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def sample_config(self):
        return ThumbnailConfig(
            size=ThumbnailSize.MEDIUM,
            format=ThumbnailFormat.WEBP,
            quality=85
        )
    
    @pytest.mark.asyncio
    async def test_get_file_hash(self, service, sample_image):
        """Test file hash generation."""
        hash1 = await service.get_file_hash(sample_image)
        hash2 = await service.get_file_hash(sample_image)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256
        assert isinstance(hash1, str)
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, service, sample_config):
        """Test cache key generation."""
        file_hash = "test_hash_123"
        cache_key = service.get_cache_key(file_hash, sample_config)
        
        expected = f"thumb:{sample_config.size.size_name}:{sample_config.format.value}:{file_hash}"
        assert cache_key == expected
    
    @pytest.mark.asyncio
    async def test_validate_image_file_success(self, service, sample_image):
        """Test successful image validation."""
        result = await service.validate_image_file(sample_image)
        
        assert result.is_valid
        assert result.metadata is not None
        assert 'format' in result.metadata
        assert 'size' in result.metadata
        assert result.file_hash is not None
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_validate_image_file_not_found(self, service):
        """Test image validation with non-existent file."""
        result = await service.validate_image_file("/nonexistent/image.jpg")
        
        assert not result.is_valid
        assert "File does not exist" in result.error_message
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail_success(self, service, sample_image, sample_config):
        """Test successful thumbnail generation."""
        with patch('app.services.enhanced_thumbnail_service.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.setex = AsyncMock()
            mock_redis.exists = AsyncMock(return_value=False)
            
            result = await service.generate_thumbnail(
                file_path=sample_image,
                config=sample_config
            )
            
            assert result.status == "ready"
            assert result.thumbnail_path is not None
            assert result.thumbnail_url is not None
            assert result.file_size > 0
            assert result.generation_time > 0
            assert not result.cache_hit
    
    @pytest.mark.asyncio
    async def test_generate_thumbnail_cache_hit(self, service, sample_image, sample_config):
        """Test thumbnail generation with cache hit."""
        cached_result = {
            "thumbnail_path": "/cached/path.jpg",
            "thumbnail_url": "/cached/url.jpg",
            "file_size": 50000
        }
        
        with patch('app.services.enhanced_thumbnail_service.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))
            
            result = await service.generate_thumbnail(
                file_path=sample_image,
                config=sample_config
            )
            
            assert result.status == "ready"
            assert result.cache_hit
            assert result.thumbnail_url == "/cached/url.jpg"
    
    @pytest.mark.asyncio
    async def test_generate_multiple_thumbnails(self, service, sample_image):
        """Test generating multiple thumbnails."""
        configs = [
            ThumbnailConfig(ThumbnailSize.SMALL, ThumbnailFormat.WEBP, 80),
            ThumbnailConfig(ThumbnailSize.MEDIUM, ThumbnailFormat.JPEG, 85)
        ]
        
        with patch('app.services.enhanced_thumbnail_service.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            mock_redis.setex = AsyncMock()
            mock_redis.exists = AsyncMock(return_value=False)
            
            results = await service.generate_multiple_thumbnails(
                file_path=sample_image,
                configs=configs
            )
            
            assert len(results) == 2
            assert all(r.status == "ready" for r in results)
            assert results[0].config.size == ThumbnailSize.SMALL
            assert results[1].config.size == ThumbnailSize.MEDIUM
    
    @pytest.mark.asyncio
    async def test_get_thumbnail_info(self, service, sample_image):
        """Test getting thumbnail information."""
        with patch('app.services.enhanced_thumbnail_service.redis_client') as mock_redis:
            mock_redis.exists = AsyncMock(return_value=False)
            
            info = await service.get_thumbnail_info(sample_image)
            
            assert 'file_hash' in info
            assert 'available_thumbnails' in info
            assert 'cache_status' in info
            assert len(info['available_thumbnails']) == len(service.default_configs)


class TestEnhancedValidationService:
    """Test cases for EnhancedValidationService."""
    
    @pytest.fixture
    def service(self):
        return EnhancedValidationService()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing."""
        img = Image.new('RGB', (800, 600), color='blue')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f.name, 'JPEG')
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def sample_video(self):
        """Create a sample video for testing."""
        # Create a simple test video using OpenCV
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            out = cv2.VideoWriter(f.name, fourcc, 1.0, (640, 480))
            
            # Write 10 frames
            for _ in range(10):
                frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                out.write(frame)
            
            out.release()
            yield f.name
        os.unlink(f.name)
    
    @pytest.mark.asyncio
    async def test_detect_file_type_image(self, service, sample_image):
        """Test file type detection for image."""
        file_type = await service._detect_file_type(Path(sample_image))
        assert file_type == 'image'
    
    @pytest.mark.asyncio
    async def test_validate_file_basic_success(self, service, sample_image):
        """Test basic file validation success."""
        result = await service.validate_file(
            file_path=sample_image,
            validation_level=ValidationLevel.BASIC
        )
        
        assert result.is_valid
        assert result.threat_level in [ThreatLevel.SAFE, ThreatLevel.UNKNOWN]
        assert result.validation_level == ValidationLevel.BASIC
        assert 'file_info' in result.__dict__
    
    @pytest.mark.asyncio
    async def test_validate_file_comprehensive(self, service, sample_image):
        """Test comprehensive file validation."""
        with patch.object(service, '_virus_scan') as mock_virus:
            mock_virus.return_value = None
            
            result = await service.validate_file(
                file_path=sample_image,
                validation_level=ValidationLevel.COMPREHENSIVE
            )
            
            assert result.is_valid
            assert result.validation_level == ValidationLevel.COMPREHENSIVE
            assert 'security_info' in result.__dict__
            mock_virus.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_image_content(self, service, sample_image):
        """Test image content validation."""
        constraints = FileConstraints(
            max_file_size=10 * 1024 * 1024,
            allowed_extensions=['jpg', 'jpeg'],
            allowed_mime_types=['image/jpeg']
        )
        
        result = ValidationResult()
        await service._validate_image_content(
            Path(sample_image), 
            constraints, 
            result
        )
        
        assert result.is_valid
        assert 'format' in result.metadata
        assert 'size' in result.metadata
        assert result.metadata['format'] == 'JPEG'
    
    @pytest.mark.asyncio
    async def test_validate_video_content(self, service, sample_video):
        """Test video content validation."""
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Mock ffprobe output
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                json.dumps({
                    'streams': [{
                        'codec_type': 'video',
                        'codec_name': 'h264',
                        'width': 640,
                        'height': 480,
                        'r_frame_rate': '30/1'
                    }],
                    'format': {
                        'duration': '10.0',
                        'bit_rate': '1000000'
                    }
                }).encode(),
                b''
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            constraints = FileConstraints(
                max_file_size=100 * 1024 * 1024,
                allowed_extensions=['mp4'],
                allowed_mime_types=['video/mp4']
            )
            
            result = ValidationResult()
            await service._validate_video_content(
                Path(sample_video),
                constraints,
                result
            )
            
            assert result.is_valid
            assert 'codec' in result.metadata
            assert result.metadata['width'] == 640
            assert result.metadata['height'] == 480
    
    @pytest.mark.asyncio
    async def test_batch_validate(self, service, sample_image, sample_video):
        """Test batch validation."""
        with patch.object(service, '_virus_scan') as mock_virus:
            mock_virus.return_value = None
            
            results = await service.batch_validate(
                file_paths=[sample_image, sample_video],
                validation_level=ValidationLevel.STANDARD
            )
            
            assert len(results) == 2
            assert all(r.is_valid for r in results)
    
    def test_get_validation_summary(self, service):
        """Test validation summary generation."""
        results = [
            ValidationResult(is_valid=True, threat_level=ThreatLevel.SAFE),
            ValidationResult(is_valid=False, threat_level=ThreatLevel.MALICIOUS),
            ValidationResult(is_valid=True, threat_level=ThreatLevel.SUSPICIOUS)
        ]
        
        summary = service.get_validation_summary(results)
        
        assert summary['total_files'] == 3
        assert summary['valid_files'] == 2
        assert summary['invalid_files'] == 1
        assert summary['threat_distribution']['safe'] == 1
        assert summary['threat_distribution']['malicious'] == 1
        assert summary['threat_distribution']['suspicious'] == 1


class TestEnhancedCacheService:
    """Test cases for EnhancedCacheService."""
    
    @pytest.fixture
    def service(self):
        return EnhancedCacheService()
    
    @pytest.mark.asyncio
    async def test_memory_cache_operations(self, service):
        """Test memory cache operations."""
        # Test set and get
        success = await service.l1_cache.set("test_key", "test_value")
        assert success
        
        entry = await service.l1_cache.get("test_key")
        assert entry is not None
        assert entry.value == "test_value"
        assert entry.access_count == 1
        
        # Test delete
        deleted = await service.l1_cache.delete("test_key")
        assert deleted
        
        entry = await service.l1_cache.get("test_key")
        assert entry is None
    
    @pytest.mark.asyncio
    async def test_disk_cache_operations(self, service):
        """Test disk cache operations."""
        # Test set and get
        success = await service.l3_cache.set("test_key", {"data": "test_value"})
        assert success
        
        entry = await service.l3_cache.get("test_key")
        assert entry is not None
        assert entry.value["data"] == "test_value"
        
        # Test delete
        deleted = await service.l3_cache.delete("test_key")
        assert deleted
    
    @pytest.mark.asyncio
    async def test_get_with_cache_miss(self, service):
        """Test cache get with miss."""
        with patch.object(service, '_get_config') as mock_config:
            mock_config.return_value = service.default_configs['metadata']
            
            result = await service.get("nonexistent_key")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_or_set(self, service):
        """Test get or set functionality."""
        call_count = 0
        
        def factory():
            nonlocal call_count
            call_count += 1
            return "computed_value"
        
        # First call should compute and cache
        result1 = await service.get_or_set("test_key", factory)
        assert result1 == "computed_value"
        assert call_count == 1
        
        # Second call should return cached value
        result2 = await service.get_or_set("test_key", factory)
        assert result2 == "computed_value"
        assert call_count == 1  # Should not call factory again
    
    @pytest.mark.asyncio
    async def test_warm_cache(self, service):
        """Test cache warming."""
        keys = ["key1", "key2", "key3"]
        
        def factory(key):
            return f"value_for_{key}"
        
        results = await service.warm_cache(keys, factory)
        
        assert len(results) == 3
        assert all(r == f"value_for_{k}" for r, k in zip(results, keys))
    
    def test_get_stats(self, service):
        """Test statistics retrieval."""
        stats = service.get_stats()
        
        assert 'operations' in stats
        assert 'l1_stats' in stats
        assert 'l3_stats' in stats
        assert 'configurations' in stats


class TestReliabilityService:
    """Test cases for ReliabilityService."""
    
    @pytest.fixture
    def service(self):
        return ReliabilityService()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_success(self, service):
        """Test circuit breaker with successful operations."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=60)
        cb = service.get_circuit_breaker("test_service", config)
        
        async def success_func():
            return "success"
        
        result = await cb.call(success_func)
        assert result == "success"
        assert cb.state.value == "closed"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_and_open(self, service):
        """Test circuit breaker opening after failures."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=1)
        cb = service.get_circuit_breaker("test_service", config)
        
        async def fail_func():
            raise ValueError("Test failure")
        
        # First failure
        with pytest.raises(ValueError):
            await cb.call(fail_func)
        assert cb.state.value == "closed"
        assert cb.failure_count == 1
        
        # Second failure should open circuit
        with pytest.raises(ValueError):
            await cb.call(fail_func)
        assert cb.state.value == "open"
        
        # Third call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(fail_func)
    
    @pytest.mark.asyncio
    async def test_retry_handler_success(self, service):
        """Test retry handler with successful operation."""
        config = RetryConfig(max_attempts=3, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
        retry_handler = service.get_retry_handler("test_service", config)
        
        call_count = 0
        
        async def sometimes_fail():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await retry_handler.execute_with_retry(sometimes_fail)
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_handler_exhausted(self, service):
        """Test retry handler exhausting attempts."""
        config = RetryConfig(max_attempts=2, strategy=RetryStrategy.FIXED_DELAY)
        retry_handler = service.get_retry_handler("test_service", config)
        
        async def always_fail():
            raise ValueError("Permanent failure")
        
        with pytest.raises(ValueError):
            await retry_handler.execute_with_retry(always_fail)
    
    @pytest.mark.asyncio
    async def test_reliable_call(self, service):
        """Test reliable call with both circuit breaker and retry."""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First failure")
            return "success"
        
        result = await service.reliable_call(
            service_name="test_service",
            func=flaky_func,
            circuit_breaker_config=CircuitBreakerConfig(failure_threshold=5),
            retry_config=RetryConfig(max_attempts=2)
        )
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_health_checker(self, service):
        """Test health checker functionality."""
        # Register a simple health check
        async def healthy_check():
            return True
        
        service.health_checker.register_check(
            service.health_checker.health_checks.__class__(
                name="test_check",
                check_func=healthy_check,
                timeout=5.0,
                critical=True
            )()
        )
        
        # Run health check
        results = await service.health_checker.check_health("test_check")
        
        assert "test_check" in results
        assert results["test_check"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_get_overall_health(self, service):
        """Test overall health assessment."""
        health_status = await service.health_checker.get_overall_health()
        
        assert "status" in health_status
        assert "message" in health_status
        assert "checks" in health_status
        assert "summary" in health_status
        assert health_status["status"] in ["healthy", "degraded", "unhealthy", "unknown"]
    
    async def test_get_reliability_stats(self, service):
        """Test reliability statistics."""
        stats = await service.get_reliability_stats()
        
        assert "circuit_breakers" in stats
        assert "health_status" in stats
        assert "timestamp" in stats


class TestIntegration:
    """Integration tests for the complete enhanced media system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_thumbnail_workflow(self):
        """Test complete thumbnail generation workflow."""
        # Create test image
        img = Image.new('RGB', (1200, 800), color='green')
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img.save(f.name, 'JPEG', quality=95)
            test_image = f.name
        
        try:
            # Initialize services
            thumbnail_service = EnhancedThumbnailService()
            validation_service = EnhancedValidationService()
            cache_service = EnhancedCacheService()
            
            # Validate image
            validation_result = await validation_service.validate_file(
                test_image,
                validation_level=ValidationLevel.STANDARD
            )
            assert validation_result.is_valid
            
            # Generate thumbnails
            configs = [
                ThumbnailConfig(ThumbnailSize.SMALL, ThumbnailFormat.WEBP, 80),
                ThumbnailConfig(ThumbnailSize.MEDIUM, ThumbnailFormat.JPEG, 85),
                ThumbnailConfig(ThumbnailSize.LARGE, ThumbnailFormat.WEBP, 90)
            ]
            
            results = await thumbnail_service.generate_multiple_thumbnails(
                test_image,
                configs
            )
            
            assert len(results) == 3
            assert all(r.status == "ready" for r in results)
            
            # Check cache
            cache_key = f"thumbnail_info:{await thumbnail_service.get_file_hash(test_image)}"
            cached_info = await cache_service.get(cache_key, 'thumbnails')
            assert cached_info is not None
            
        finally:
            os.unlink(test_image)
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        reliability_service = ReliabilityService()
        
        # Create a circuit breaker that will open
        config = CircuitBreakerConfig(failure_threshold=1, timeout=0.1)
        cb = reliability_service.get_circuit_breaker("failing_service", config)
        
        failure_count = 0
        
        async def failing_service():
            nonlocal failure_count
            failure_count += 1
            raise ConnectionError("Service unavailable")
        
        # First call should fail and open circuit
        with pytest.raises(ConnectionError):
            await cb.call(failing_service)
        
        assert cb.state.value == "open"
        
        # Subsequent calls should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_service)
        
        # Wait for timeout and test recovery
        await asyncio.sleep(0.2)
        
        async def recovering_service():
            return "recovered"
        
        # Circuit should be half-open and recover
        result = await cb.call(recovering_service)
        assert result == "recovered"
        assert cb.state.value == "closed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])