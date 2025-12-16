from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.ar_content import ARContent

router = APIRouter()


@router.get("/ar/{unique_id}/content")
async def get_public_ar_content(unique_id: str, db: AsyncSession = Depends(get_db)):
    """Get public AR content data for the viewer template."""
    stmt = select(ARContent).where(ARContent.unique_id == unique_id, ARContent.is_active == True)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found or inactive")
    
    return {
        "id": ac.id,
        "unique_id": str(ac.unique_id),
        "name": ac.name,
        "image_url": ac.image_url,
        "video_url": ac.video_url,
        "qr_code_url": ac.qr_code_url,
        "preview_url": ac.preview_url,
        "content_metadata": ac.content_metadata,
    }


@router.get("/ar-content/{unique_id}")
async def get_public_ar_content_redirect(unique_id: str, db: AsyncSession = Depends(get_db)):
    """Alias endpoint for /ar/{unique_id}/content for cleaner URLs."""
    # This is the same as the above but with a cleaner path structure
    return await get_public_ar_content(unique_id, db)
