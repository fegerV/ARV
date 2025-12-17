"""
Hierarchical routes for company → project → ar-content structure
"""
from fastapi import APIRouter
from app.api.routes import companies, projects, ar_content

# Create hierarchical router for companies → projects → ar-content
hierarchical_router = APIRouter(prefix="/api")

# Companies routes
hierarchical_router.include_router(companies.router, prefix="/companies", tags=["Companies"])

# Projects routes under companies
hierarchical_router.include_router(projects.router, prefix="/projects", tags=["Projects"])

# AR Content routes under projects (with company context)
hierarchical_router.include_router(ar_content.router, prefix="/ar-content", tags=["AR Content"])