#!/usr/bin/env python3
"""Create initial data for testing"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import get_settings
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from datetime import datetime, timedelta

async def create_test_data():
    """Create test data for admin panel testing"""
    settings = get_settings()
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Check if Vertex AR company exists
            result = await session.execute(select(Company).where(Company.name == "Vertex AR"))
            company = result.scalar_one_or_none()
            
            if not company:
                # Create Vertex AR company
                company = Company(
                    name="Vertex AR",
                    slug="vertex-ar",
                    contact_email="admin@vertexar.com",
                    status="active"
                )
                session.add(company)
                await session.flush()  # Get the ID
                print(f"Created company: {company.name}")
            else:
                print(f"Company already exists: {company.name}")
            
            # Check if "Портреты" project exists
            result = await session.execute(select(Project).where(
                (Project.name == "Портреты") & (Project.company_id == company.id)
            ))
            project = result.scalar_one_or_none()
            
            if not project:
                # Create "Портреты" project
                project = Project(
                    name="Портреты",
                    company_id=company.id,
                    status="active"
                )
                session.add(project)
                await session.flush()  # Get the ID
                print(f"Created project: {project.name}")
            else:
                print(f"Project already exists: {project.name}")
            
            await session.commit()
            print(f"Test data created successfully!")
            print(f"Company ID: {company.id}")
            print(f"Project ID: {project.id}")
            return True
            
        except Exception as e:
            print(f"Error creating test data: {e}")
            return False
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_test_data())