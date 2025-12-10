import unittest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from app.services.thumbnail_service import ThumbnailService


class TestThumbnailService(unittest.TestCase):
    """Test cases for ThumbnailService"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.service = ThumbnailService()
        self.test_image_data = b"fake_image_data_for_testing"
        
    def test_init(self):
        """Test ThumbnailService initialization"""
        self.assertIsInstance(self.service, ThumbnailService)
        self.assertEqual(self.service.thumbnail_size, (320, 240))
        self.assertEqual(self.service.quality, 85)
    
    @patch('app.services.thumbnail_service.Image')
    def test_generate_image_thumbnail_success(self, mock_image):
        """Test successful image thumbnail generation"""
        # Mock PIL Image
        mock_img_instance = Mock()
        mock_image.open.return_value.__enter__.return_value = mock_img_instance
        mock_img_instance.mode = 'RGB'
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_file.write(self.test_image_data)
            tmp_file_path = tmp_file.name
        
        try:
            # Test thumbnail generation
            result = asyncio.run(self.service.generate_image_thumbnail(
                image_path=tmp_file_path,
                thumbnail_name="test_thumb.jpg"
            ))
            
            # Assertions
            self.assertEqual(result["status"], "ready")
            self.assertIn("thumbnail_path", result)
            self.assertIn("thumbnail_url", result)
            self.assertTrue(result["thumbnail_url"].startswith("/storage/content/thumbnails/"))
            
            # Verify mocks were called correctly
            mock_image.open.assert_called_once_with(tmp_file_path)
            # We can't easily verify the Resampling.LANCZOS call, so we'll just check thumbnail was called
            mock_img_instance.thumbnail.assert_called_once()
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    @patch('app.services.thumbnail_service.Image')
    def test_generate_image_thumbnail_with_transparency(self, mock_image):
        """Test image thumbnail generation with transparency conversion"""
        # Mock PIL Image with transparency
        mock_img_instance = Mock()
        mock_image.open.return_value.__enter__.return_value = mock_img_instance
        mock_img_instance.mode = 'RGBA'  # Transparent mode
        mock_img_instance.convert.return_value = mock_img_instance  # Return same instance after convert
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(self.test_image_data)
            tmp_file_path = tmp_file.name
        
        try:
            # Test thumbnail generation
            result = asyncio.run(self.service.generate_image_thumbnail(
                image_path=tmp_file_path,
                thumbnail_name="test_thumb.png"
            ))
            
            # Assertions
            self.assertEqual(result["status"], "ready")
            mock_img_instance.convert.assert_called_once_with('RGB')
        finally:
            # Clean up
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    @patch('app.services.thumbnail_service.Image')
    def test_generate_image_thumbnail_failure(self, mock_image):
        """Test image thumbnail generation failure"""
        # Mock PIL Image to raise exception
        mock_image.open.side_effect = Exception("Failed to open image")
        
        # Test thumbnail generation with invalid file
        result = asyncio.run(self.service.generate_image_thumbnail(
            image_path="/nonexistent/image.jpg",
            thumbnail_name="test_thumb.jpg"
        ))
        
        # Assertions
        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to open image")
    
    def test_generate_video_thumbnail_nonexistent_file(self):
        """Test video thumbnail generation with nonexistent file"""
        # Test thumbnail generation with nonexistent file
        result = asyncio.run(self.service.generate_video_thumbnail(
            video_path="/nonexistent/video.mp4",
            thumbnail_name="test_video_thumb.jpg"
        ))
        
        # Assertions
        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)
    
    def test_validate_thumbnail_success(self):
        """Test successful thumbnail validation"""
        # Create a temporary image file for validation
        with patch('app.services.thumbnail_service.Image') as mock_image:
            mock_img_instance = Mock()
            mock_image.open.return_value.__enter__.return_value = mock_img_instance
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_file.write(b"fake_thumbnail_data")
                tmp_file_path = tmp_file.name
                # Set file size to be within valid range
                os.truncate(tmp_file_path, 50000)  # 50KB
            
            try:
                # Test validation
                result = asyncio.run(self.service.validate_thumbnail(tmp_file_path))
                
                # Assertions
                self.assertTrue(result)
            finally:
                # Clean up
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
    
    def test_validate_thumbnail_failure_invalid_size(self):
        """Test thumbnail validation failure due to invalid size"""
        # Create a temporary image file that's too small
        with patch('app.services.thumbnail_service.Image') as mock_image:
            mock_img_instance = Mock()
            mock_image.open.return_value.__enter__.return_value = mock_img_instance
            
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_file.write(b"x")  # Very small file
                tmp_file_path = tmp_file.name
            
            try:
                # Test validation
                result = asyncio.run(self.service.validate_thumbnail(tmp_file_path))
                
                # Assertions
                self.assertFalse(result)
            finally:
                # Clean up
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)


if __name__ == '__main__':
    unittest.main()