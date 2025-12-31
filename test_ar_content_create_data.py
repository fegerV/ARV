#!/usr/bin/env python3
"""
Test script to verify AR content creation route data
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.company import Company
from app.models.project import Project
from app.html.routes.ar_content import ar_content_create
from fastapi import Request
from unittest.mock import Mock


async def test_ar_content_create_data():
    """Test the data being passed to AR content creation template"""
    
    # Setup database
    DATABASE_URL = 'sqlite+aiosqlite:///./vertex_ar.db'
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get companies and projects like the route does
        companies_query = select(Company)
        companies_result = await session.execute(companies_query)
        companies = []
        for company in companies_result.scalars().all():
            companies.append({
                "id": company.id,
                "name": company.name,
                "contact_email": company.contact_email,
                "status": company.status,
                "created_at": company.created_at,
                "updated_at": company.updated_at
            })
        
        # Get all projects
        projects_query = select(Project)
        projects_result = await session.execute(projects_query)
        projects = []
        for project in projects_result.scalars().all():
            projects.append({
                "id": project.id,
                "name": project.name,
                "company_id": project.company_id,
                "status": project.status,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            })
        
        print("=== COMPANIES ===")
        for company in companies:
            print(f"ID: {company['id']} (type: {type(company['id'])}), Name: {company['name']}")
        
        print("\n=== PROJECTS ===")
        for project in projects:
            print(f"ID: {project['id']} (type: {type(project['id'])}), Name: {project['name']}, Company ID: {project['company_id']} (type: {type(project['company_id'])})")
        
        # Test JavaScript data conversion (like in the route)
        companies_js = [
            {
                "id": company.get("id"),
                "name": company.get("name"),
                "status": company.get("status"),
                "contact_email": company.get("contact_email"),
                "created_at": (company.get("created_at").isoformat() if company.get("created_at") and hasattr(company.get("created_at"), "isoformat")
                              else str(company.get("created_at")) if company.get("created_at") else None),
                "updated_at": (company.get("updated_at").isoformat() if company.get("updated_at") and hasattr(company.get("updated_at"), "isoformat")
                              else str(company.get("updated_at")) if company.get("updated_at") else None),
            }
            for company in companies
        ]
        
        projects_js = [
            {
                "id": project.get("id"),
                "name": project.get("name"),
                "company_id": project.get("company_id"),
                "status": project.get("status"),
                "created_at": (project.get("created_at").isoformat() if project.get("created_at") and hasattr(project.get("created_at"), "isoformat")
                              else str(project.get("created_at")) if project.get("created_at") else None),
                "updated_at": (project.get("updated_at").isoformat() if project.get("updated_at") and hasattr(project.get("updated_at"), "isoformat")
                              else str(project.get("updated_at")) if project.get("updated_at") else None),
            }
            for project in projects
        ]
        
        print("\n=== JAVASCRIPT DATA ===")
        print("Companies JS:", companies_js)
        print("Projects JS:", projects_js)
        
        # Test the filtering logic (like in the frontend)
        print("\n=== FILTERING TEST ===")
        test_company_id = 1
        filtered_projects = [p for p in projects_js if str(p["company_id"]) == str(test_company_id)]
        print(f"Projects for company {test_company_id}: {filtered_projects}")
        
        print("\n=== TYPE CONVERSION TEST ===")
        for project in projects_js:
            project_company_id = project["company_id"]
            selected_company_id = test_company_id
            matches = str(project_company_id) == str(selected_company_id)
            print(f"Project {project['name']}: company_id={project_company_id} (type: {type(project_company_id)}) vs {selected_company_id} (type: {type(selected_company_id)}) -> {matches}")


if __name__ == "__main__":
    asyncio.run(test_ar_content_create_data())