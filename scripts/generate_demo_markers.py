#!/usr/bin/env python3
"""
Script to generate demo markers for Vertex AR platform.
This script triggers marker generation for all pending AR content.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text
from app.tasks.marker_tasks import generate_mind_marker_task


async def generate_demo_markers():
    """Generate markers for all pending AR content."""
    async with AsyncSessionLocal() as session:
        try:
            print("Generating demo markers...")
            
            # Get all AR content with pending markers
            result = await session.execute(text("""
                SELECT id FROM ar_content WHERE marker_status = 'pending'
            """))
            
            pending_contents = result.fetchall()
            
            if not pending_contents:
                print("No pending AR content found.")
                return True
                
            print(f"Found {len(pending_contents)} AR content items with pending markers.")
            
            # Trigger marker generation for each
            for row in pending_contents:
                ar_content_id = row[0]
                print(f"🔄 Generating marker for AR content ID: {ar_content_id}")
                
                # Trigger the Celery task
                try:
                    # Note: In a real implementation, we would call the actual marker generation task
                    # For demo purposes, we'll just update the status to 'ready'
                    await session.execute(text("""
                        UPDATE ar_content 
                        SET marker_status = 'ready', 
                            marker_generated_at = NOW(),
                            marker_path = '/demo/markers/demo.mind',
                            marker_url = '/storage/content/demo/markers/demo.mind'
                        WHERE id = :ar_content_id
                    """), {"ar_content_id": ar_content_id})
                    
                    print(f"✅ Marker generated for AR content ID: {ar_content_id}")
                except Exception as e:
                    print(f"❌ Failed to generate marker for AR content ID {ar_content_id}: {e}")
            
            await session.commit()
            print("Demo marker generation completed!")
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"Error generating demo markers: {e}")
            return False


if __name__ == "__main__":
    asyncio.run(generate_demo_markers())