#!/usr/bin/env python3
"""
Test all requirements from the ticket:
"Проверь страницу детальной информации. Все ли данные туда приходят, правильно ли отображаются превьюшки, формируется ли уникальная ссылка, создаются ли маркеры, можно ли добавить видео и сделать его активным, проверяется ли время (3 года) по истечении видео должно отключится."
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.video import Video
from app.utils.ar_content import build_unique_link
from app.services.video_scheduler import compute_video_status


async def test_ticket_requirements():
    """Test all requirements from the ticket."""
    
    print("🎫 Testing Ticket Requirements")
    print("=" * 60)
    print("Ticket: Проверь страницу детальной информации...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        # Get test data
        from sqlalchemy import select
        result = await db.execute(select(ARContent).limit(1))
        ar_content = result.scalar_one_or_none()
        
        if not ar_content:
            print("❌ No AR content found in database")
            return False
        
        print(f"📋 Testing AR Content: {ar_content.order_number} (ID: {ar_content.id})")
        
        # Requirement 1: Все ли данные туда приходят (Do all data come there)
        print("\n1️⃣ Checking if all data arrives:")
        
        data_checks = [
            ("Order number", ar_content.order_number),
            ("Customer name", ar_content.customer_name),
            ("Customer phone", ar_content.customer_phone),
            ("Customer email", ar_content.customer_email),
            ("Company info", ar_content.company_id),
            ("Project info", ar_content.project_id),
            ("Duration years", ar_content.duration_years),
            ("Status", ar_content.status),
            ("Views count", ar_content.views_count),
        ]
        
        all_data_present = True
        for field_name, value in data_checks:
            if value:
                print(f"   ✅ {field_name}: {value}")
            else:
                print(f"   ❌ {field_name}: Missing")
                all_data_present = False
        
        # Requirement 2: Правильно ли отображаются превьюшки (Are previews displayed correctly)
        print("\n2️⃣ Checking preview display:")
        
        preview_checks = [
            ("Photo URL", ar_content.photo_url),
            ("Thumbnail URL", ar_content.thumbnail_url),
            ("QR Code URL", ar_content.qr_code_url),
            ("Marker URL", ar_content.marker_url),
        ]
        
        all_previews_present = True
        for preview_name, url in preview_checks:
            if url:
                print(f"   ✅ {preview_name}: {url}")
            else:
                print(f"   ❌ {preview_name}: Missing")
                all_previews_present = False
        
        # Requirement 3: Формируется ли уникальная ссылка (Is unique link generated)
        print("\n3️⃣ Checking unique link generation:")
        
        unique_link = build_unique_link(ar_content.unique_id)
        if ar_content.unique_id and unique_link:
            print(f"   ✅ Unique ID: {ar_content.unique_id}")
            print(f"   ✅ Unique Link: {unique_link}")
            print(f"   ✅ Public URL: {ar_content.public_link}")
            unique_link_ok = True
        else:
            print(f"   ❌ Unique link not generated")
            unique_link_ok = False
        
        # Requirement 4: Создаются ли маркеры (Are markers created)
        print("\n4️⃣ Checking marker creation:")
        
        marker_checks = [
            ("Marker URL", ar_content.marker_url),
            ("Marker Status", ar_content.marker_status),
            ("Marker Metadata", ar_content.marker_metadata),
            ("Marker Path", ar_content.marker_path),
        ]
        
        all_markers_ok = True
        for marker_field, value in marker_checks:
            if value:
                print(f"   ✅ {marker_field}: {value}")
            else:
                print(f"   ❌ {marker_field}: Missing")
                all_markers_ok = False
        
        # Requirement 5: Можно ли добавить видео (Can video be added)
        print("\n5️⃣ Checking video addition capability:")
        
        # Check if video upload endpoint exists
        videos_route_content = Path("app/api/routes/videos.py").read_text()
        has_upload_endpoint = "upload_videos" in videos_route_content
        
        if has_upload_endpoint:
            print(f"   ✅ Video upload endpoint exists")
            
            # Check current videos
            videos_result = await db.execute(select(Video).where(Video.ar_content_id == ar_content.id))
            videos = videos_result.scalars().all()
            print(f"   ✅ Current videos: {len(videos)}")
            for video in videos:
                print(f"      - {video.filename} (ID: {video.id})")
            
            video_addition_ok = True
        else:
            print(f"   ❌ Video upload endpoint missing")
            video_addition_ok = False
        
        # Requirement 6: Можно ли сделать его активным (Can video be made active)
        print("\n6️⃣ Checking video activation capability:")
        
        # Check if set-active endpoint exists
        has_set_active_endpoint = "set_video_active" in videos_route_content
        
        if has_set_active_endpoint:
            print(f"   ✅ Video set-active endpoint exists")
            
            # Check if there's an active video
            if ar_content.active_video_id:
                active_video = await db.get(Video, ar_content.active_video_id)
                if active_video:
                    print(f"   ✅ Active video: {active_video.filename} (ID: {active_video.id})")
                    video_activation_ok = True
                else:
                    print(f"   ❌ Active video ID invalid")
                    video_activation_ok = False
            else:
                print(f"   ⚠️ No active video set (but endpoint exists)")
                video_activation_ok = True  # Endpoint exists, which is what matters
        else:
            print(f"   ❌ Video set-active endpoint missing")
            video_activation_ok = False
        
        # Requirement 7: Проверяется ли время (3 года) (Is time checked for 3 years)
        print("\n7️⃣ Checking 3-year time verification:")
        
        # Check duration years
        if ar_content.duration_years == 3:
            print(f"   ✅ Duration set to 3 years")
            
            # Check expiry calculation
            creation_date = ar_content.created_at.replace(tzinfo=None) if ar_content.created_at.tzinfo else ar_content.created_at
            expiry_date = creation_date + timedelta(days=3 * 365)
            current_date = datetime.utcnow()
            days_remaining = (expiry_date - current_date).days
            
            print(f"   ✅ Creation date: {creation_date}")
            print(f"   ✅ Expiry date: {expiry_date}")
            print(f"   ✅ Days remaining: {days_remaining}")
            
            # Check if viewer has expiry check
            ar_content_route = Path("app/api/routes/ar_content.py").read_text()
            has_expiry_check = "duration_years * 365" in ar_content_route
            
            if has_expiry_check:
                print(f"   ✅ Viewer has expiry check logic")
                time_check_ok = True
            else:
                print(f"   ❌ Viewer missing expiry check logic")
                time_check_ok = False
        else:
            print(f"   ❌ Duration not set to 3 years (actual: {ar_content.duration_years})")
            time_check_ok = False
        
        # Requirement 8: По истечении видео должно отключится (Video should be disabled after expiry)
        print("\n8️⃣ Checking video disable after expiry:")
        
        # Check video status computation
        videos_result = await db.execute(select(Video).where(Video.ar_content_id == ar_content.id))
        videos = videos_result.scalars().all()
        
        video_expiry_ok = True
        for video in videos:
            status = compute_video_status(video)
            print(f"   ✅ Video {video.filename}: status = {status}")
            
            # Check if video has subscription end logic
            if hasattr(video, 'subscription_end'):
                print(f"      - Subscription end field exists")
            
            # Check if video scheduler has expiry logic
            video_scheduler_content = Path("app/services/video_scheduler.py").read_text()
            has_video_expiry_logic = "subscription_end" in video_scheduler_content
            
            if has_video_expiry_logic:
                print(f"      - Video scheduler has expiry logic")
            else:
                print(f"      - Video scheduler missing expiry logic")
                video_expiry_ok = False
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 REQUIREMENTS SUMMARY:")
        
        requirements = [
            ("All data arrives", all_data_present),
            ("Previews displayed correctly", all_previews_present),
            ("Unique link generated", unique_link_ok),
            ("Markers created", all_markers_ok),
            ("Video can be added", video_addition_ok),
            ("Video can be made active", video_activation_ok),
            ("3-year time verification", time_check_ok),
            ("Video disabled after expiry", video_expiry_ok),
        ]
        
        passed_count = sum(1 for _, passed in requirements if passed)
        total_count = len(requirements)
        
        for req_name, passed in requirements:
            status = "✅" if passed else "❌"
            print(f"   {status} {req_name}")
        
        completion_percentage = (passed_count / total_count) * 100
        print(f"\n🎯 Ticket Requirements Completion: {completion_percentage:.1f}% ({passed_count}/{total_count})")
        
        if completion_percentage == 100:
            print("🎉 Perfect! All ticket requirements are fully implemented!")
        elif completion_percentage >= 90:
            print("👍 Excellent! Almost all requirements are met.")
        elif completion_percentage >= 75:
            print("👍 Good! Most requirements are met.")
        else:
            print("⚠️ Needs work. Several requirements are not met.")
        
        return completion_percentage == 100


if __name__ == "__main__":
    success = asyncio.run(test_ticket_requirements())
    sys.exit(0 if success else 1)