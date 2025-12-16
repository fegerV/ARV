import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch
import asyncio

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.thumbnail_service import (
    THUMBNAIL_GENERATION_COUNT,
    THUMBNAIL_GENERATION_DURATION,
    THUMBNAIL_UPLOAD_COUNT,
    THUMBNAIL_UPLOAD_DURATION
)
from prometheus_client import CollectorRegistry, generate_latest, REGISTRY


class TestPrometheusMetrics(unittest.TestCase):
    """Test cases for Prometheus metrics"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a separate registry for testing
        self.registry = CollectorRegistry()
        
        # Reinitialize metrics with test registry
        self.thumbnail_generation_count = THUMBNAIL_GENERATION_COUNT
        self.thumbnail_generation_duration = THUMBNAIL_GENERATION_DURATION
        self.thumbnail_upload_count = THUMBNAIL_UPLOAD_COUNT
        self.thumbnail_upload_duration = THUMBNAIL_UPLOAD_DURATION

    def test_thumbnail_generation_count_metrics(self):
        """Test thumbnail generation count metrics"""
        # Get initial values
        initial_image_value = self.thumbnail_generation_count.labels(type='image', status='success')._value.get()
        initial_video_value = self.thumbnail_generation_count.labels(type='video', status='failure')._value.get()
        
        # Increment metrics
        self.thumbnail_generation_count.labels(type='image', status='success').inc()
        self.thumbnail_generation_count.labels(type='video', status='failure').inc()
        
        # Check that metrics are incremented
        new_image_value = self.thumbnail_generation_count.labels(type='image', status='success')._value.get()
        new_video_value = self.thumbnail_generation_count.labels(type='video', status='failure')._value.get()
        
        self.assertEqual(new_image_value, initial_image_value + 1.0)
        self.assertEqual(new_video_value, initial_video_value + 1.0)

    def test_thumbnail_generation_duration_metrics(self):
        """Test thumbnail generation duration metrics"""
        # Record duration
        self.thumbnail_generation_duration.labels(type='image').observe(0.5)
        self.thumbnail_generation_duration.labels(type='video').observe(1.2)
        
        # For histogram metrics, we just verify they don't throw exceptions when observed
        # Actual testing of histogram values is complex and not necessary for basic functionality
        pass

    def test_thumbnail_upload_count_metrics(self):
        """Test thumbnail upload count metrics"""
        # Get initial values
        initial_local_value = self.thumbnail_upload_count.labels(provider='local', status='success')._value.get()
        initial_minio_value = self.thumbnail_upload_count.labels(provider='minio', status='failure')._value.get()
        
        # Increment metrics
        self.thumbnail_upload_count.labels(provider='local', status='success').inc()
        self.thumbnail_upload_count.labels(provider='minio', status='failure').inc()
        
        # Check that metrics are incremented
        new_local_value = self.thumbnail_upload_count.labels(provider='local', status='success')._value.get()
        new_minio_value = self.thumbnail_upload_count.labels(provider='minio', status='failure')._value.get()
        
        self.assertEqual(new_local_value, initial_local_value + 1.0)
        self.assertEqual(new_minio_value, initial_minio_value + 1.0)

    def test_thumbnail_upload_duration_metrics(self):
        """Test thumbnail upload duration metrics"""
        # Record duration
        self.thumbnail_upload_duration.labels(provider='local').observe(0.3)
        self.thumbnail_upload_duration.labels(provider='minio').observe(0.8)
        
        # For histogram metrics, we just verify they don't throw exceptions when observed
        # Actual testing of histogram values is complex and not necessary for basic functionality
        pass


if __name__ == '__main__':
    unittest.main()