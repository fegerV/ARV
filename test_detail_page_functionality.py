#!/usr/bin/env python3
"""
Comprehensive test script to check all features on the AR content detail page.
Verifies that all required information and functionality is available.
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import get_db, AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.project import Project
from app.models.video import Video


async def check_detail_page_features():
    """Check all features available on the AR content detail page."""
    
    print("🔍 AR Content Detail Page Feature Analysis")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Get first AR content to analyze
        result = await db.execute(select(ARContent).limit(1))
        ar_content = result.scalar_one_or_none()
        
        if not ar_content:
            print("❌ No AR content found in database")
            return
        
        print(f"📋 Analyzing AR Content: {ar_content.order_number} (ID: {ar_content.id})")
        print("=" * 50)
        
        # Check all required fields
        fields_to_check = [
            ("Basic Info", ["id", "order_number", "customer_name", "customer_phone", "customer_email"]),
            ("Media Files", ["photo_url", "video_url", "thumbnail_url", "qr_code_url"]),
            ("AR Markers", ["marker_url", "marker_status", "marker_metadata"]),
            ("Storage", ["photo_path", "video_path", "qr_code_path", "marker_path"]),
            ("Metadata", ["duration_years", "status", "views_count", "content_metadata"]),
            ("Timestamps", ["created_at", "updated_at"]),
            ("Relations", ["company_id", "project_id", "active_video_id"]),
            ("Public Links", ["unique_id"]),
        ]
        
        for category, field_names in fields_to_check:
            print(f"\n📂 {category}:")
            for field_name in field_names:
                if hasattr(ar_content, field_name):
                    value = getattr(ar_content, field_name)
                    status = "✅" if value is not None else "⚠️"
                    print(f"  {status} {field_name}: {value}")
                else:
                    print(f"  ❌ {field_name}: NOT FOUND")
        
        # Check related data
        print("\n🏢 Related Data:")
        print("-" * 30)
        
        # Company info
        if ar_content.company_id:
            company = await db.get(Company, ar_content.company_id)
            if company:
                print(f"✅ Company: {company.name} (ID: {company.id})")
            else:
                print(f"❌ Company ID {ar_content.company_id} not found")
        
        # Project info
        if ar_content.project_id:
            project = await db.get(Project, ar_content.project_id)
            if project:
                print(f"✅ Project: {project.name} (ID: {project.id})")
            else:
                print(f"❌ Project ID {ar_content.project_id} not found")
        
        # Videos
        videos_result = await db.execute(
            select(Video).where(Video.ar_content_id == ar_content.id)
        )
        videos = videos_result.scalars().all()
        
        print(f"\n🎥 Videos ({len(videos)} found):")
        for video in videos:
            active_marker = "🟢 ACTIVE" if video.is_active else "⚪"
            print(f"  {active_marker} {video.filename} (ID: {video.id})")
            print(f"    - URL: {video.video_url}")
            print(f"    - Size: {video.size_bytes} bytes")
            print(f"    - Duration: {video.duration}s")
            print(f"    - Resolution: {video.width}x{video.height}")
            print(f"    - Status: {video.status}")
        
        # Check what's missing for complete functionality
        print("\n🔍 Feature Analysis:")
        print("-" * 30)
        missing_features = []
        
        # Check preview photo
        if not ar_content.photo_url:
            missing_features.append("Preview photo")
        else:
            print("✅ Preview photo: Available")
        
        # Check video
        if not ar_content.video_url and not videos:
            missing_features.append("Video content")
        elif videos:
            print("✅ Video content: Available")
        else:
            print("⚠️ Video content: Only legacy video_url")
        
        # Check QR code
        if not ar_content.qr_code_url:
            missing_features.append("QR code")
        else:
            print("✅ QR code: Available")
        
        # Check AR marker
        if not ar_content.marker_url:
            missing_features.append("AR marker")
        else:
            print("✅ AR marker: Available")
        
        # Check customer info completeness
        customer_info = []
        if ar_content.customer_name:
            customer_info.append("name")
        if ar_content.customer_phone:
            customer_info.append("phone")
        if ar_content.customer_email:
            customer_info.append("email")
        
        if len(customer_info) >= 2:
            print(f"✅ Customer info: {', '.join(customer_info)}")
        else:
            missing_features.append("Complete customer information")
        
        # Check storage path
        if not ar_content.photo_path:
            missing_features.append("File storage paths")
        else:
            print("✅ File storage paths: Available")
        
        # Check unique link
        if not ar_content.unique_id:
            missing_features.append("Unique link")
        else:
            print("✅ Unique link: Available")
        
        # Check file quality/size info
        if videos:
            has_metadata = any(v.width and v.height and v.size_bytes for v in videos)
            if has_metadata:
                print("✅ Video quality/size info: Available")
            else:
                missing_features.append("Video quality/size information")
        
        # Check NFT marker size
        if not ar_content.marker_metadata:
            missing_features.append("NFT marker size configuration")
        else:
            print("✅ NFT marker configuration: Available")
        
        # Check active video selection
        if len(videos) > 1:
            print("✅ Multiple videos: Active video selection available")
        elif len(videos) == 1:
            print("✅ Single video: Active by default")
        else:
            missing_features.append("Active video selection")
        
        # Check subscription management
        if ar_content.duration_years:
            print(f"✅ Subscription duration: {ar_content.duration_years} years")
        else:
            missing_features.append("Subscription duration")
        
        # Summary
        print("\n📋 Summary:")
        print("-" * 30)
        
        if missing_features:
            print(f"⚠️ Missing features ({len(missing_features)}):")
            for feature in missing_features:
                print(f"  - {feature}")
        else:
            print("✅ All features available!")
        
        print(f"\n🎯 Overall completeness: {100 - len(missing_features) * 10}%")
        
        # Template analysis
        print("\n📄 Template Analysis:")
        print("-" * 30)
        
        template_path = Path("templates/ar-content/detail.html")
        if template_path.exists():
            template_content = template_path.read_text()
            
            template_features = {
                "Preview photo lightbox": "showPortraitLightbox",
                "QR code modal": "showQRDialog",
                "Video upload": "showUploadDialog",
                "Delete confirmation": "showDeleteDialog",
                "Copy link": "copyLink",
                "Download QR": "downloadQR",
                "Video upload handler": "handleVideoUpload",
                "Delete handler": "handleDelete"
            }
            
            print("Template features:")
            for feature, js_function in template_features.items():
                if js_function in template_content:
                    print(f"  ✅ {feature}")
                else:
                    print(f"  ❌ {feature} - {js_function} not found")
        else:
            print("❌ Template file not found")
        
        # API endpoints analysis
        print("\n🔍 API Endpoints Analysis:")
        print("-" * 30)
        
        required_endpoints = [
            "GET /ar-content/{id}",
            "POST /ar-content/{content_id}/videos",
            "PATCH /ar-content/{content_id}/videos/{video_id}/set-active",
            "DELETE /ar-content/{content_id}",
            "GET /ar-content/{content_id}/videos"
        ]
        
        # Check if endpoints exist by searching in route files
        api_files = [
            "app/api/routes/ar_content.py",
            "app/api/routes/videos.py"
        ]
        
        for endpoint in required_endpoints:
            found = False
            method = endpoint.split(" ")[0]
            path_pattern = endpoint.split(" ")[1]
            
            for api_file in api_files:
                file_path = Path(api_file)
                if file_path.exists():
                    content = file_path.read_text()
                    
                    # More flexible pattern matching
                    if method.lower() in content.lower():
                        # Check for path pattern with variations
                        patterns = [
                            path_pattern,
                            path_pattern.replace("{content_id}", "{id}"),
                            path_pattern.replace("{content_id}", "{content_id}"),
                            path_pattern.replace("{video_id}", "{video_id}")
                        ]
                        
                        for pattern in patterns:
                            # Remove braces for matching but keep slashes
                            search_pattern = pattern.replace("{", "").replace("}", "")
                            # Check for exact path segments
                            if f'"/{search_pattern}"' in content or f'"{search_pattern}"' in content or f"/{search_pattern}" in content:
                                found = True
                                break
                    
                    if found:
                        break
            
            if found:
                print(f"  ✅ {endpoint}")
            else:
                print(f"  ❌ {endpoint} - Not found")
        
        # Check specific functionality requirements from the ticket
        print("\n🎫 Ticket Requirements Check:")
        print("-" * 30)
        
        requirements = {
            "Preview photo": ar_content.photo_url is not None,
            "Video content": len(videos) > 0 or ar_content.video_url is not None,
            "QR code": ar_content.qr_code_url is not None,
            "Lightbox functionality": "showPortraitLightbox" in template_content if template_path.exists() else False,
            "Company info": ar_content.company_id is not None,
            "Project info": ar_content.project_id is not None,
            "Customer name": ar_content.customer_name is not None,
            "Customer phone": ar_content.customer_phone is not None,
            "Customer email": ar_content.customer_email is not None,
            "File storage path": ar_content.photo_path is not None,
            "Unique link": ar_content.unique_id is not None,
            "Photo size/quality": any(v.width and v.height for v in videos) if videos else False,
            "NFT marker size": ar_content.marker_metadata is not None,
            "Active video selection": len(videos) > 0,
            "Add new video": "handleVideoUpload" in template_content if template_path.exists() else False,
            "Make video active": "set_video_active" in Path("app/api/routes/videos.py").read_text() if Path("app/api/routes/videos.py").exists() else False,
            "Change storage duration": ar_content.duration_years is not None,
            "Save functionality": "form" in template_content.lower() if template_path.exists() else False,
            "Delete functionality": "handleDelete" in template_content if template_path.exists() else False
        }
        
        for requirement, available in requirements.items():
            status = "✅" if available else "❌"
            print(f"  {status} {requirement}")
        
        completed_count = sum(requirements.values())
        total_count = len(requirements)
        completion_rate = (completed_count / total_count) * 100
        
        print(f"\n🎯 Ticket Requirements Completion: {completion_rate:.1f}% ({completed_count}/{total_count})")
        
        if completion_rate >= 90:
            print("🎉 Excellent! Almost all requirements are met.")
        elif completion_rate >= 75:
            print("👍 Good! Most requirements are met.")
        elif completion_rate >= 50:
            print("⚠️ Fair. Some important features are missing.")
        else:
            print("❌ Poor. Many critical features are missing.")


if __name__ == "__main__":
    asyncio.run(check_detail_page_features())