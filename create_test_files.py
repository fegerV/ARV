#!/usr/bin/env python3
"""Create test image and video files"""

from PIL import Image, ImageDraw
import os

def create_test_image(path, size=(400, 400), color="blue"):
    """Create a test image"""
    img = Image.new('RGB', size, color)
    draw = ImageDraw.Draw(img)
    
    # Add some text
    draw.text((50, 50), "Test Image", fill="white")
    draw.text((50, 100), f"Size: {size[0]}x{size[1]}", fill="white")
    
    img.save(path)
    print(f"Created test image: {path}")

def create_test_files():
    """Create test files for AR content"""
    base_dir = "storage/content"
    
    # Create test images
    create_test_image(f"{base_dir}/images/test_portrait_1.jpg", (800, 600), "darkblue")
    create_test_image(f"{base_dir}/images/test_portrait_2.jpg", (600, 800), "darkgreen")
    
    # Create thumbnail versions
    create_test_image(f"{base_dir}/thumbnails/test_thumb_1.jpg", (200, 150), "blue")
    create_test_image(f"{base_dir}/thumbnails/test_thumb_2.jpg", (150, 200), "green")
    
    print("Test files created successfully!")

if __name__ == "__main__":
    create_test_files()