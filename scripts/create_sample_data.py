#!/usr/bin/env python3
"""
Enhanced script to create comprehensive sample data for testing AR content functionality.

This script creates:
- 2-3 sample companies
- 2-3 projects per company  
- 3-5 AR content items per project
- Test images, videos, thumbnails, QR codes
- Populates all new columns with realistic data
"""

import asyncio
import os
import sys
import random
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from uuid import uuid4
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.config import settings
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.enums import CompanyStatus, ProjectStatus, ArContentStatus, VideoStatus


def create_dummy_image(file_path: Path, size_mb: float = 0.5) -> None:
    """Create a dummy image file with realistic size."""
    # Create a simple JPEG header + random data
    jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00'
    image_data = jpeg_header + os.urandom(int(size_mb * 1024 * 1024))
    
    with open(file_path, 'wb') as f:
        f.write(image_data)


def create_dummy_video(file_path: Path, size_mb: float = 2.0) -> None:
    """Create a dummy video file with realistic size."""
    # Create a simple MP4 header + random data
    mp4_header = b'\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00mp42isom\x00\x00\x00\x00'
    video_data = mp4_header + os.urandom(int(size_mb * 1024 * 1024))
    
    with open(file_path, 'wb') as f:
        f.write(video_data)


def create_dummy_qr_code(file_path: Path) -> None:
    """Create a dummy QR code image."""
    # Simple PNG header + square pattern
    png_header = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x02\x00\x00\x00\xfc\x18\xed\xa3'
    qr_data = png_header + b'\x00' * 1000  # Simplified QR code data
    
    with open(file_path, 'wb') as f:
        f.write(qr_data)


def create_dummy_thumbnail(file_path: Path) -> None:
    """Create a dummy thumbnail image."""
    create_dummy_image(file_path, size_mb=0.1)  # Smaller size for thumbnails


# Sample data generators
COMPANY_NAMES = [
    "TechCorp Solutions",
    "Creative Agency Pro", 
    "Retail Innovations Ltd"
]

PROJECT_NAMES = [
    "Product Launch Campaign",
    "Brand Experience",
    "Customer Engagement",
    "Interactive Marketing",
    "Digital Showcase",
    "AR Experience Zone"
]

CUSTOMER_NAMES = [
    "John Smith", "Emma Johnson", "Michael Brown", "Sarah Davis", "James Wilson",
    "Maria Garcia", "Robert Martinez", "Jennifer Anderson", "David Taylor", "Lisa Thomas"
]

CUSTOMER_EMAILS = [
    "john.smith@example.com", "emma.j@company.com", "m.brown@business.com",
    "sarah.davis@corp.com", "j.wilson@enterprise.com", "maria.g@org.com"
]

CUSTOMER_PHONES = [
    "+1-555-0101", "+1-555-0102", "+1-555-0103", "+1-555-0104", "+1-555-0105"
]

DURATION_YEARS = [1, 3, 5]


async def create_sample_data():
    """Create comprehensive sample data."""
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            print("🚀 Starting sample data creation...")
            
            # Create sample companies
            companies = []
            for i, company_name in enumerate(COMPANY_NAMES[:3]):  # Create 3 companies
                company = Company(
                    name=company_name,
                    contact_email=f"contact@{company_name.lower().replace(' ', '')}.com",
                    status=CompanyStatus.ACTIVE
                )
                session.add(company)
                await session.flush()
                companies.append(company)
                print(f"✅ Created company: {company.name} (ID: {company.id})")
            
            # Create projects for each company
            all_projects = []
            for company in companies:
                for j, project_name in enumerate(random.sample(PROJECT_NAMES, 3)):  # 3 projects per company
                    project = Project(
                        name=f"{project_name} - {company.name}",
                        status=ProjectStatus.ACTIVE,
                        company_id=company.id
                    )
                    session.add(project)
                    await session.flush()
                    all_projects.append(project)
                    print(f"  📁 Created project: {project.name} (ID: {project.id})")
            
            # Create AR content for each project
            all_ar_content = []
            content_counter = 1
            
            for project in all_projects:
                # Create 3-5 AR content items per project
                num_content = random.randint(3, 5)
                
                for k in range(num_content):
                    unique_id = str(uuid4())
                    order_number = f"ORD-{content_counter:04d}"
                    
                    # Create directory structure for this AR content
                    content_dir = Path(settings.LOCAL_STORAGE_PATH) / "ar_content" / str(unique_id)
                    content_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create sample files
                    image_path = content_dir / "main_image.jpg"
                    qr_path = content_dir / "qr_code.png"
                    thumbnail_path = content_dir / "thumbnail.jpg"
                    
                    create_dummy_image(image_path)
                    create_dummy_qr_code(qr_path)
                    create_dummy_thumbnail(thumbnail_path)
                    
                    # Create AR content
                    ar_content = ARContent(
                        project_id=project.id,
                        unique_id=unique_id,
                        order_number=order_number,
                        customer_name=random.choice(CUSTOMER_NAMES),
                        customer_phone=random.choice(CUSTOMER_PHONES),
                        customer_email=random.choice(CUSTOMER_EMAILS),
                        duration_years=random.choice(DURATION_YEARS),
                        views_count=random.randint(0, 1000),
                        status=random.choice([ArContentStatus.PENDING, ArContentStatus.ACTIVE, ArContentStatus.ARCHIVED]),
                        photo_path=str(image_path),
                        photo_url=f"/storage/ar_content/{unique_id}/main_image.jpg",
                        qr_code_path=str(qr_path),
                        qr_code_url=f"/storage/ar_content/{unique_id}/qr_code.png",
                        content_metadata={
                            "created_by": "sample_data_script",
                            "image_size_mb": 0.5,
                            "generated_at": datetime.utcnow().isoformat()
                        }
                    )
                    session.add(ar_content)
                    await session.flush()
                    all_ar_content.append(ar_content)
                    
                    print(f"    🎯 Created AR content: {ar_content.order_number} - {ar_content.customer_name} (ID: {ar_content.id})")
                    
                    # Create videos for this AR content
                    num_videos = random.randint(1, 3)  # 1-3 videos per AR content
                    
                    for l in range(num_videos):
                        video_dir = content_dir / "videos"
                        video_dir.mkdir(parents=True, exist_ok=True)
                        
                        video_filename = f"video_{l+1}.mp4"
                        video_path = video_dir / video_filename
                        video_size_mb = random.uniform(1.0, 5.0)
                        
                        create_dummy_video(video_path, video_size_mb)
                        
                        video = Video(
                            ar_content_id=ar_content.id,
                            filename=video_filename,
                            duration=random.randint(10, 300),  # 10 seconds to 5 minutes
                            size=int(video_size_mb * 1024 * 1024),  # Convert to bytes
                            video_status=random.choice([VideoStatus.UPLOADED, VideoStatus.PROCESSING, VideoStatus.READY])
                        )
                        session.add(video)
                        await session.flush()
                        
                        print(f"      🎬 Created video: {video.filename} ({video.duration}s, {video_size_mb:.1f}MB)")
                    
                    # Set the first video as active if we have videos
                    if hasattr(ar_content, 'videos') and ar_content.videos:
                        ar_content.active_video_id = ar_content.videos[0].id
                    
                    content_counter += 1
            
            await session.commit()
            
            # Print summary
            print("\n📊 Sample Data Creation Summary:")
            print(f"  Companies: {len(companies)}")
            print(f"  Projects: {len(all_projects)}")
            print(f"  AR Content: {len(all_ar_content)}")
            
            total_videos = sum(len(ac.videos) if hasattr(ac, 'videos') else 0 for ac in all_ar_content)
            print(f"  Videos: {total_videos}")
            
            # Calculate storage usage
            storage_path = Path(settings.LOCAL_STORAGE_PATH)
            total_files = 0
            total_size = 0
            
            if storage_path.exists():
                for item in storage_path.rglob("*"):
                    if item.is_file():
                        total_files += 1
                        total_size += item.stat().st_size
            
            print(f"  Storage Files: {total_files}")
            print(f"  Storage Size: {total_size / (1024*1024):.2f} MB")
            
            print("\n✨ Sample data created successfully!")
            print(f"📂 Storage location: {storage_path}")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating sample data: {e}")
            raise
        finally:
            await session.close()


if __name__ == "__main__":
    asyncio.run(create_sample_data())