#!/usr/bin/env python3
"""
Script to upload video to AR content via API
"""
import requests
import sys
from pathlib import Path

def upload_video(content_id: int, video_path: str, base_url: str = "http://127.0.0.1:8000"):
    """
    Upload video to AR content via API
    
    Args:
        content_id: AR content ID
        video_path: Path to video file
        base_url: Base URL of the API server
    """
    # Note: videos router is registered with prefix "/api/videos" in main.py
    # So the full path is /api/videos/ar-content/{content_id}/videos
    url = f"{base_url}/api/videos/ar-content/{content_id}/videos"
    
    # Check if video file exists
    video_file = Path(video_path)
    if not video_file.exists():
        print(f"[ERROR] Video file not found: {video_path}")
        return None
    
    print(f"[*] Uploading video: {video_file.name}")
    print(f"    Content ID: {content_id}")
    print(f"    File size: {video_file.stat().st_size / (1024*1024):.2f} MB")
    
    # Prepare file for upload
    # Note: FastAPI expects files with parameter name matching the endpoint parameter
    # The endpoint uses `videos: List[UploadFile] = File(...)`
    # So we need to use 'videos' as the parameter name and provide a list
    try:
        with open(video_file, 'rb') as f:
            # For List[UploadFile], we need to provide a list of tuples
            # Each tuple: (field_name, (filename, file_object, content_type))
            files = [
                ('videos', (video_file.name, f, 'video/mp4'))
            ]
            
            response = requests.post(url, files=files, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Success! Uploaded {len(result.get('videos', []))} video(s)")
                print(f"\nUpload Result:")
                for video in result.get('videos', []):
                    print(f"  - Video ID: {video.get('id')}")
                    print(f"    Title: {video.get('title')}")
                    print(f"    Status: {video.get('status')}")
                    print(f"    Is Active: {video.get('is_active')}")
                    print(f"    URL: {video.get('video_url')}")
                return result
            else:
                print(f"[ERROR] Status: {response.status_code}")
                print(f"    Response: {response.text}")
                return None
                
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to server at {base_url}")
        print("    Make sure the server is running!")
        return None
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python upload_video_api.py <content_id> <video_path> [base_url]")
        print("\nExample:")
        print("  python upload_video_api.py 3 test_data/test_video.mp4")
        print("  python upload_video_api.py 3 test_data/test_video.mp4 http://127.0.0.1:8000")
        sys.exit(1)
    
    content_id = int(sys.argv[1])
    video_path = sys.argv[2]
    base_url = sys.argv[3] if len(sys.argv) > 3 else "http://127.0.0.1:8000"
    
    result = upload_video(content_id, video_path, base_url)
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
