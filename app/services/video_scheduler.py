from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.video_rotation_schedule import VideoRotationSchedule


async def get_active_video(ar_content_id: int, db: AsyncSession) -> Optional[Video]:
    """Return the currently active video for AR content.
    Priority:
    1) ARContent.active_video_id
    2) Any video with schedule range matching now and is_active
    3) Any video marked active
    4) First available video (by rotation_order or id)
    """
    now = datetime.utcnow()

    ac = await db.get(ARContent, ar_content_id)
    if not ac:
        return None

    # 1) ARContent.active_video_id
    if ac.active_video_id:
        v = await db.get(Video, ac.active_video_id)
        if v:
            return v

    # 2) Seasonal/date-specific via video schedule_start/schedule_end
    stmt = (
        select(Video)
        .where(Video.ar_content_id == ar_content_id)
        .where(Video.is_active == True)
        .where(Video.schedule_start != None)
        .where(Video.schedule_end != None)
    )
    res = await db.execute(stmt)
    for v in res.scalars().all():
        if v.schedule_start and v.schedule_end and v.schedule_start <= now <= v.schedule_end:
            return v

    # 3) Any currently active video
    stmt_active = select(Video).where(Video.ar_content_id == ar_content_id, Video.is_active == True)
    res_active = await db.execute(stmt_active)
    v_active = res_active.scalars().first()
    if v_active:
        return v_active

    # 4) Fallback: first by rotation_order then id
    stmt_any = (
        select(Video)
        .where(Video.ar_content_id == ar_content_id)
        .order_by(Video.rotation_order.asc(), Video.id.asc())
    )
    res_any = await db.execute(stmt_any)
    return res_any.scalars().first()
