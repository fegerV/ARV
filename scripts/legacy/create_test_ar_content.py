#!/usr/bin/env python3
"""
Create test AR content for detail page analysis.
"""

import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.project import Project
from app.models.video import Video


async def create_test_data():
    """Create test AR content with all features."""
    
    async with AsyncSessionLocal() as db:
        # Create company
        company = Company(
            name="Vertex AR",
            slug="vertex-ar",
            contact_email="admin@vertexar.com",
            status="active"
        )
        db.add(company)
        await db.commit()
        await db.refresh(company)
        
        # Create project
        project = Project(
            name="Портреты",
            company_id=company.id,
            status="active"
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        
        # Create AR content
        ar_content = ARContent(
            company_id=company.id,
            project_id=project.id,
            unique_id=str(uuid.uuid4()),
            order_number="ORD-20251230-0001",
            customer_name="Иван Петров",
            customer_phone="+7 (999) 123-45-67",
            customer_email="ivan.petrov@example.com",
            duration_years=3,
            photo_url="/storage/content/portrait.jpg",
            photo_path="/storage/content/portrait.jpg",
            video_url="/storage/content/video.mp4",
            video_path="/storage/content/video.mp4",
            thumbnail_url="/storage/thumbnails/portrait_thumb.jpg",
            qr_code_url="/storage/qr/qr_code.png",
            qr_code_path="/storage/qr/qr_code.png",
            marker_url="/storage/markers/marker.mind",
            marker_path="/storage/markers/marker.mind",
            marker_status="ready",
            marker_metadata={"size": "512x512", "format": "mindar"},
            status="ready",
            views_count=42,
            content_metadata={"test": True}
        )
        db.add(ar_content)
        await db.commit()
        await db.refresh(ar_content)
        
        # Create videos
        video1 = Video(
            ar_content_id=ar_content.id,
            filename="video1.mp4",
            video_path="/storage/content/video1.mp4",
            video_url="/storage/content/video1.mp4",
            thumbnail_path="/storage/thumbnails/video1_thumb.jpg",
            preview_url="/storage/content/video1.mp4",
            duration=30,
            width=1920,
            height=1080,
            size_bytes=5242880,
            mime_type="video/mp4",
            status="ready",
            is_active=True,
            rotation_type="none",
            rotation_order=0
        )
        db.add(video1)
        
        video2 = Video(
            ar_content_id=ar_content.id,
            filename="video2.mp4",
            video_path="/storage/content/video2.mp4",
            video_url="/storage/content/video2.mp4",
            thumbnail_path="/storage/thumbnails/video2_thumb.jpg",
            preview_url="/storage/content/video2.mp4",
            duration=45,
            width=1280,
            height=720,
            size_bytes=3145728,
            mime_type="video/mp4",
            status="ready",
            is_active=False,
            rotation_type="none",
            rotation_order=1
        )
        db.add(video2)
        
        await db.commit()
        await db.refresh(video1)
        await db.refresh(video2)
        
        # Set active video
        ar_content.active_video_id = video1.id
        await db.commit()
        
        print("✅ Test data created successfully!")
        print(f"Company: {company.name} (ID: {company.id})")
        print(f"Project: {project.name} (ID: {project.id})")
        print(f"AR Content: {ar_content.order_number} (ID: {ar_content.id})")
        print(f"Videos: {len([video1, video2])} created")
        print(f"Active video: {video1.filename}")


if __name__ == "__main__":
    asyncio.run(create_test_data())
