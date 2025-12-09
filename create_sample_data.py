#!/usr/bin/env python3
"""
Script to create sample data for testing AR content functionality
"""

import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from uuid import uuid4
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video

async def create_sample_data():
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if we have a default company
            res = await session.execute(select(Company).where(Company.is_default == True))
            company = res.scalar_one_or_none()
            
            if not company:
                print("No default company found. Please run the application first to seed default data.")
                return
            
            print(f"Using company: {company.name} (ID: {company.id})")
            
            # Check if we have any projects
            res = await session.execute(select(Project).where(Project.company_id == company.id))
            projects = res.scalars().all()
            
            if not projects:
                # Create a sample project
                project = Project(
                    company_id=company.id,
                    name="Sample Project",
                    slug="sample-project",
                    description="Sample project for testing AR content"
                )
                session.add(project)
                await session.flush()
                print(f"Created project: {project.name} (ID: {project.id})")
            else:
                project = projects[0]
                print(f"Using existing project: {project.name} (ID: {project.id})")
            
            # Create sample AR content
            unique_id = uuid4()
            content_dir = Path(settings.STORAGE_BASE_PATH) / "ar_content" / str(unique_id)
            content_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a dummy image file
            image_path = content_dir / "sample_image.jpg"
            with open(image_path, "w") as f:
                f.write("This is a dummy image file for testing purposes")
            
            ar_content = ARContent(
                project_id=project.id,
                company_id=company.id,
                unique_id=unique_id,
                title="Sample AR Content",
                description="This is a sample AR content for testing",
                client_name="Test Client",
                client_phone="+1234567890",
                client_email="test@example.com",
                image_path=str(image_path),
                image_url=f"/storage/ar_content/{unique_id}/sample_image.jpg",
                marker_status="ready",
                is_active=True
            )
            session.add(ar_content)
            await session.flush()
            print(f"Created AR content: {ar_content.title} (ID: {ar_content.id})")
            
            # Create a sample video
            video_dir = content_dir / "videos"
            video_dir.mkdir(parents=True, exist_ok=True)
            video_path = video_dir / "sample_video.mp4"
            with open(video_path, "w") as f:
                f.write("This is a dummy video file for testing purposes")
            
            video = Video(
                ar_content_id=ar_content.id,
                video_path=str(video_path),
                video_url=f"/storage/ar_content/{unique_id}/videos/sample_video.mp4",
                title="Sample Video",
                duration=30.0,
                is_active=True
            )
            session.add(video)
            await session.flush()
            print(f"Created video: {video.title} (ID: {video.id})")
            
            # Set the active video for the AR content
            ar_content.active_video_id = video.id
            
            await session.commit()
            print("Sample data created successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"Error creating sample data: {e}")
            raise
        finally:
            await session.close()

if __name__ == "__main__":
    asyncio.run(create_sample_data())