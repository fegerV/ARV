#!/usr/bin/env python3
"""
Test script to create a simple test image for MindAR marker generation
"""
from PIL import Image, ImageDraw
import numpy as np

# Create a simple test image with distinctive features
def create_test_image():
    # Create a 500x500 image with some geometric patterns
    img = Image.new('RGB', (500, 500), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some distinctive patterns
    # Large square border
    draw.rectangle([50, 50, 450, 450], outline='black', width=10)
    
    # Corner markers
    draw.rectangle([70, 70, 130, 130], fill='black')
    draw.rectangle([370, 70, 430, 130], fill='black')
    draw.rectangle([70, 370, 130, 430], fill='black')
    draw.rectangle([370, 370, 430, 430], fill='black')
    
    # Center circle
    draw.ellipse([200, 200, 300, 300], fill='black')
    
    # Cross pattern
    draw.rectangle([240, 100, 260, 400], fill='gray')
    draw.rectangle([100, 240, 400, 260], fill='gray')
    
    # Save the image
    img.save('/tmp/test_marker_image.jpg', 'JPEG', quality=95)
    print("Test image saved to /tmp/test_marker_image.jpg")

if __name__ == "__main__":
    create_test_image()