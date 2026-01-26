#!/usr/bin/env python3
"""
Script to fix AR content status - update status to 'ready' for content with ready markers
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def fix_ar_content_status():
    """Update status to 'ready' for AR content with ready markers"""
    async with AsyncSessionLocal() as db:
        try:
            # Find all AR content with marker_status='ready' but status='pending'
            stmt = select(ARContent).where(
                ARContent.marker_status == "ready",
                ARContent.status == "pending"
            )
            result = await db.execute(stmt)
            ar_contents = result.scalars().all()
            
            if not ar_contents:
                print("[OK] No AR content found with ready markers but pending status")
            else:
                print(f"[*] Found {len(ar_contents)} AR content items to update")
                
                # Update status to 'ready'
                update_stmt = (
                    update(ARContent)
                    .where(
                        ARContent.marker_status == "ready",
                        ARContent.status == "pending"
                    )
                    .values(status="ready")
                )
                
                result = await db.execute(update_stmt)
                await db.commit()
                
                print(f"[OK] Updated {result.rowcount} AR content items from 'pending' to 'ready'")
                
                # Show details
                for ar_content in ar_contents:
                    print(f"  - AR Content ID {ar_content.id}: {ar_content.order_number}")
            
            # Also check for content with marker_status='ready_with_warnings' or 'ready_invalid'
            stmt2 = select(ARContent).where(
                ARContent.marker_status.in_(["ready", "ready_with_warnings", "ready_invalid"]),
                ARContent.status == "pending"
            )
            result2 = await db.execute(stmt2)
            ar_contents2 = result2.scalars().all()
            
            if ar_contents2:
                print(f"\n[*] Found {len(ar_contents2)} additional AR content items with ready markers (including warnings)")
                
                update_stmt2 = (
                    update(ARContent)
                    .where(
                        ARContent.marker_status.in_(["ready", "ready_with_warnings", "ready_invalid"]),
                        ARContent.status == "pending"
                    )
                    .values(status="ready")
                )
                
                result2 = await db.execute(update_stmt2)
                await db.commit()
                
                print(f"[OK] Updated {result2.rowcount} additional AR content items from 'pending' to 'ready'")
                
                for ar_content in ar_contents2:
                    print(f"  - AR Content ID {ar_content.id}: {ar_content.order_number} (marker_status: {ar_content.marker_status})")
                
        except Exception as e:
            await db.rollback()
            print(f"[ERROR] Failed to update AR content status: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(fix_ar_content_status())
