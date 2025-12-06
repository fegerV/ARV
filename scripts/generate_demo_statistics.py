#!/usr/bin/env python3
"""
Script to generate demo statistics for Vertex AR platform.
This script populates the ar_view_sessions table with realistic demo data.
"""

import asyncio
import sys
import os
import uuid
import random
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text


async def generate_demo_statistics():
    """Generate demo statistics by populating ar_view_sessions table."""
    async with AsyncSessionLocal() as session:
        try:
            print("Generating demo statistics...")
            
            # Insert demo view sessions for all AR content created in the last day
            await session.execute(text("""
                INSERT INTO ar_view_sessions 
                (ar_content_id, project_id, company_id, session_id, device_type, os, browser, 
                 duration_seconds, tracking_quality, video_played, country, city, created_at)
                SELECT 
                  ac.id,
                  ac.project_id,
                  ac.company_id,
                  :session_id,
                  CASE WHEN random() > 0.5 THEN 'mobile' ELSE 'tablet' END,
                  CASE WHEN random() > 0.7 THEN 'Android' ELSE 'iOS' END,
                  CASE WHEN random() > 0.5 THEN 'Chrome' ELSE 'Safari' END,
                  ROUND(random() * 60 + 10)::int,
                  CASE WHEN random() > 0.8 THEN 'excellent' WHEN random() > 0.5 THEN 'good' ELSE 'fair' END,
                  TRUE,
                  CASE WHEN random() > 0.7 THEN 'Russia' ELSE 'United States' END,
                  CASE WHEN random() > 0.7 THEN 'Moscow' ELSE 'New York' END,
                  NOW() - (random() * INTERVAL '30 days')
                FROM ar_content ac
                WHERE ac.created_at > NOW() - INTERVAL '1 day'
            """), {"session_id": str(uuid.uuid4())})
            
            # Update views count on AR content based on generated sessions
            await session.execute(text("""
                UPDATE ar_content 
                SET views_count = (
                    SELECT COUNT(*) 
                    FROM ar_view_sessions 
                    WHERE ar_view_sessions.ar_content_id = ar_content.id
                ),
                last_viewed_at = NOW()
                WHERE id IN (
                    SELECT DISTINCT ar_content_id 
                    FROM ar_view_sessions
                )
            """))
            
            await session.commit()
            print("Demo statistics generated successfully!")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"Error generating demo statistics: {e}")
            return False


if __name__ == "__main__":
    asyncio.run(generate_demo_statistics())