"""
Nested/ hierarchical routes for company → project → ar-content structure
"""
from fastapi import APIRouter
from app.api.routes import companies, projects, ar_content

# Create the hierarchical structure
nested_router = APIRouter(prefix="/api")

# Companies routes (top level)
nested_router.include_router(companies.router, prefix="/companies", tags=["Companies"])

# Projects routes (nested under companies)
nested_router.include_router(projects.router, prefix="/companies/{company_id}/projects", tags=["Projects"])

# AR Content routes (nested under projects, which are under companies)
# This would require a custom approach since we need: /companies/{company_id}/projects/{project_id}/ar-content