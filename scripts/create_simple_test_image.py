#!/usr/bin/env python3
"""
Create a simple test image using built-in Python libraries
"""
import base64
import struct

# Create a simple 24-bit BMP image with distinctive patterns
def create_simple_bmp():
    width, height = 200, 200
    
    # BMP header (54 bytes)
    bmp_header = bytearray(54)
    bmp_header[0:2] = b'BM'  # Signature
    bmp_header[2:6] = struct.pack('<I', 54 + width * height * 3)  # File size
    bmp_header[10:14] = struct.pack('<I', 54)  # Data offset
    bmp_header[14:18] = struct.pack('<I', 40)  # Header size
    bmp_header[18:22] = struct.pack('<I', width)  # Width
    bmp_header[22:26] = struct.pack('<I', height)  # Height
    bmp_header[26:28] = struct.pack('<H', 1)  # Planes
    bmp_header[28:30] = struct.pack('<H', 24)  # Bits per pixel
    bmp_header[34:38] = struct.pack('<I', width * height * 3)  # Image size
    
    # Create image data with simple pattern
    image_data = bytearray()
    for y in range(height):
        for x in range(width):
            # Create a checkerboard pattern with some distinctive features
            if (x < 50 and y < 50) or (x >= 150 and y >= 150):
                # Black corners
                r, g, b = 0, 0, 0
            elif 80 <= x <= 120 and 80 <= y <= 120:
                # Black center square
                r, g, b = 0, 0, 0
            elif abs(x - y) < 5 or abs(x + y - height) < 5:
                # Diagonal lines
                r, g, b = 128, 128, 128
            else:
                # White background
                r, g, b = 255, 255, 255
            
            # BMP stores pixels in BGR order
            image_data.extend([b, g, r])
    
    # Write BMP file
    with open('/tmp/test_marker_image.bmp', 'wb') as f:
        f.write(bmp_header)
        f.write(image_data)
    
    print("Test BMP image saved to /tmp/test_marker_image.bmp")

if __name__ == "__main__":
    create_simple_bmp()