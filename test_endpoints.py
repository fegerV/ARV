#!/usr/bin/env python3
"""Test script to verify all endpoints are accessible."""

import asyncio
from app.main import app

def test_endpoints():
    """Test that all expected endpoints are registered."""
    
    # List of expected endpoints from the audit report
    expected_endpoints = [
        # Auth endpoints (should work)
        "POST /api/auth/login",
        "POST /api/auth/logout",
        "GET /api/auth/me",
        "POST /api/auth/register",
        
        # Companies endpoints (should work)
        "GET /api/companies/",
        "GET /api/companies/{company_id}",
        "POST /api/companies/",
        "PUT /api/companies/{company_id}",
        "DELETE /api/companies/{company_id}",
        
        # Projects endpoints (should work)
        "GET /api/projects/projects",
        "GET /api/projects/companies/{company_id}/projects",
        "POST /api/projects/projects",
        "GET /api/projects/projects/{project_id}",
        "PUT /api/projects/projects/{project_id}",
        "DELETE /api/projects/projects/{project_id}",
        
        # AR Content endpoints (should work)
        "GET /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content",
        "POST /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/new",
        "GET /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/{content_id}",
        "PUT /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/{content_id}",
        "PATCH /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/{content_id}/video",
        "DELETE /api/ar-content/companies/{company_id}/projects/{project_id}/ar-content/{content_id}",
        
        # Storage endpoints (should work)
        "POST /api/storage/storage/connections",
        "POST /api/storage/storage/connections/{connection_id}/test",
        "GET /api/storage/storage/connections/{connection_id}/stats",
        "PUT /api/storage/companies/{company_id}/storage",
        "GET /api/storage/storage/connections",
        
        # Analytics endpoints (should work)
        "GET /api/analytics/analytics/overview",
        "GET /api/analytics/analytics/summary",
        "GET /api/analytics/analytics/companies/{company_id}",
        "GET /api/analytics/analytics/company/{company_id}",
        "GET /api/analytics/analytics/projects/{project_id}",
        "GET /api/analytics/analytics/ar-content/{content_id}",
        "POST /api/analytics/analytics/ar-session",
        "POST /api/analytics/mobile/sessions",
        "POST /api/analytics/mobile/analytics",
        
        # Notifications endpoints (should work)
        "GET /api/notifications/notifications",
        "POST /api/notifications/notifications/mark-read",
        "DELETE /api/notifications/notifications/{notification_id}",
        "POST /api/notifications/notifications/test",
        
        # System endpoints (should work)
        "GET /",
        "GET /ar/{unique_id}",
        "GET /favicon.ico",
        "GET /api/health/status",
        
        # Rotation endpoints (were missing)
        "POST /api/rotation/ar-content/{content_id}/rotation",
        "PUT /api/rotation/rotation/{schedule_id}",
        "DELETE /api/rotation/rotation/{schedule_id}",
        "POST /api/rotation/ar-content/{content_id}/rotation/sequence",
        "GET /api/rotation/ar-content/{content_id}/rotation/calendar",
        
        # OAuth endpoints (were missing)
        "GET /api/oauth/yandex/authorize",
        "GET /api/oauth/yandex/callback",
        "GET /api/oauth/yandex/{connection_id}/folders",
        "POST /api/oauth/yandex/{connection_id}/create-folder",
        
        # Public endpoints (were missing)
        "GET /api/public/ar/{unique_id}/content",
        "GET /api/public/ar-content/{unique_id}",
        
        # Settings endpoints (were missing)
        "GET /api/settings/settings",
        
        # Viewer endpoints (were missing)
        "GET /api/viewer/viewer/{ar_content_id}/active-video",
        "GET /api/viewer/ar/{unique_id}/active-video",
        
        # Videos endpoints (were missing)
        "POST /api/videos/ar-content/{content_id}/videos",
        "GET /api/videos/ar-content/{content_id}/videos",
        "PATCH /api/videos/ar-content/{content_id}/videos/{video_id}/set-active",
        "PATCH /api/videos/ar-content/{content_id}/videos/{video_id}/subscription",
        "PATCH /api/videos/ar-content/{content_id}/videos/{video_id}/rotation",
        "GET /api/videos/ar-content/{content_id}/videos/{video_id}/schedules",
        "POST /api/videos/ar-content/{content_id}/videos/{video_id}/schedules",
        "PATCH /api/videos/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}",
        "DELETE /api/videos/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}",
        "PUT /api/videos/videos/{video_id}",
        "DELETE /api/videos/videos/{video_id}",
        
        # Health endpoints (were missing)
        "GET /api/health/metrics",
        
        # WebSocket endpoints (were missing)
        "WS /api/ws/alerts",
    ]
    
    # Get all registered routes
    registered_routes = []
    for route in app.routes:
        methods = getattr(route, "methods", ["GET"])
        path = getattr(route, "path", "")
        for method in methods:
            registered_routes.append(f"{method} {path}")
    
    print(f"Total registered routes: {len(registered_routes)}")
    
    # Print all registered routes for debugging
    print("\nRegistered routes:")
    for route in sorted(registered_routes):
        print(f"  {route}")
    
    # Check which endpoints are missing
    missing_endpoints = []
    found_endpoints = []
    
    for expected in expected_endpoints:
        found = False
        expected_parts = expected.split()
        if len(expected_parts) < 2:
            continue
        expected_path = expected_parts[1]  # Extract path
        for registered in registered_routes:
            registered_parts = registered.split()
            if len(registered_parts) < 2:
                continue
            registered_path = registered_parts[1]  # Extract path
            # Simple matching for now (could be improved)
            if expected_path == registered_path:
                found = True
                found_endpoints.append(expected)
                break
        if not found:
            missing_endpoints.append(expected)
    
    print(f"\nFound endpoints: {len(found_endpoints)}")
    print(f"Missing endpoints: {len(missing_endpoints)}")
    
    if missing_endpoints:
        print("\nMissing endpoints:")
        for endpoint in missing_endpoints:
            print(f"  {endpoint}")
    else:
        print("\nAll endpoints are registered!")

if __name__ == "__main__":
    test_endpoints()