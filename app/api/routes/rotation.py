from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.video_rotation_schedule import VideoRotationSchedule

router = APIRouter()


@router.post("/ar-content/{content_id}/rotation")
async def set_rotation(content_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    # Check if schedule already exists
    stmt = select(VideoRotationSchedule).where(VideoRotationSchedule.ar_content_id == content_id)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if existing:
        # Update existing schedule
        for k, v in payload.items():
            if hasattr(existing, k) and k != 'id':
                setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return {"id": existing.id}
    
    # Create new schedule
    sched = VideoRotationSchedule(
        ar_content_id=content_id,
        rotation_type=payload.get("rotation_type", "fixed"),
        default_video_id=payload.get("default_video_id"),
        date_rules=payload.get("date_rules", []),
        video_sequence=payload.get("video_sequence", []),
        current_index=payload.get("current_index", 0),
        random_seed=payload.get("random_seed"),
        no_repeat_days=payload.get("no_repeat_days", 1),
        time_of_day=payload.get("time_of_day"),
        day_of_week=payload.get("day_of_week"),
        day_of_month=payload.get("day_of_month"),
        cron_expression=payload.get("cron_expression"),
        is_active=payload.get("is_active", True),
        notify_before_expiry_days=payload.get("notify_before_expiry_days", 7),
    )
    db.add(sched)
    await db.flush()
    await db.commit()
    await db.refresh(sched)
    return {"id": sched.id}


@router.put("/rotation/{schedule_id}")
async def update_rotation(schedule_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    sched = await db.get(VideoRotationSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Rotation schedule not found")
    for k, v in payload.items():
        if hasattr(sched, k) and k != 'id':
            setattr(sched, k, v)
    await db.commit()
    await db.refresh(sched)
    return {"status": "updated", "id": sched.id}


@router.delete("/rotation/{schedule_id}")
async def delete_rotation(schedule_id: int, db: AsyncSession = Depends(get_db)):
    sched = await db.get(VideoRotationSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Rotation schedule not found")
    await db.delete(sched)
    await db.commit()
    return {"status": "deleted"}


@router.post("/ar-content/{content_id}/rotation/sequence")
async def set_rotation_sequence(content_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Set or update the video sequence for a content's rotation schedule."""
    seq = payload.get("video_sequence")
    if not isinstance(seq, list) or not seq:
        raise HTTPException(status_code=400, detail="video_sequence must be a non-empty array of video IDs")
    res = await db.execute(select(VideoRotationSchedule).where(VideoRotationSchedule.ar_content_id == content_id))
    sched = res.scalars().first()
    if not sched:
        sched = VideoRotationSchedule(ar_content_id=content_id, rotation_type="daily_cycle", video_sequence=seq, current_index=0, is_active=True)
        db.add(sched)
    else:
        sched.video_sequence = seq
        sched.current_index = 0
    await db.commit()
    return {"status": "sequence_set", "count": len(seq)}


@router.get("/ar-content/{content_id}/rotation/calendar")
async def rotation_calendar(content_id: int, month: str, db: AsyncSession = Depends(get_db)):
    """Return a naive calendar of planned videos for the given month (YYYY-MM).
    Date-specific per-video schedules override rotation sequence; otherwise daily cycle modulo.
    """
    from datetime import datetime, timedelta
    import calendar
    from app.models.video import Video

    try:
        first_day = datetime.strptime(month + "-01", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM")
    days_in_month = calendar.monthrange(first_day.year, first_day.month)[1]

    # Fetch videos and schedule
    vids_res = await db.execute(select(Video).where(Video.ar_content_id == content_id).order_by(Video.rotation_order.asc(), Video.id.asc()))
    vids = vids_res.scalars().all()
    sched_res = await db.execute(select(VideoRotationSchedule).where(VideoRotationSchedule.ar_content_id == content_id))
    sched = sched_res.scalars().first()
    seq = sched.video_sequence if sched and sched.video_sequence else [v.id for v in vids]

    calendar_map = []
    for d in range(1, days_in_month + 1):
        day = first_day.replace(day=d)
        # per-video schedule overrides
        chosen = None
        for v in vids:
            if v.schedule_start and v.schedule_end and v.schedule_start <= day <= v.schedule_end:
                chosen = v
                break
        if not chosen and seq:
            idx = day.toordinal() % len(seq)
            # fallback to id lookup
            vid_id = seq[idx]
            chosen = next((v for v in vids if v.id == vid_id), None)
        calendar_map.append({
            "date": day.strftime("%Y-%m-%d"),
            "video_id": chosen.id if chosen else None,
            "title": chosen.title if chosen else None
        })
    return {"month": month, "days": calendar_map}
