"""API routes for video rotation schedules.

Mounted at ``/api/rotation`` in ``main.py``.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.routes.auth import get_current_user_optional
from app.models.video_rotation_schedule import VideoRotationSchedule

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_auth(current_user) -> None:
    """Raise 401 if user is not authenticated."""
    if not current_user or not getattr(current_user, "is_active", False):
        raise HTTPException(status_code=401, detail="Authentication required")


def _sanitise_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce types that arrive as strings from the frontend."""
    clean: Dict[str, Any] = {}
    for key, value in payload.items():
        if key == "id":
            continue
        if key == "default_video_id":
            if value is None or value == "" or value == "null":
                clean[key] = None
            else:
                clean[key] = int(value)
        elif key in ("no_repeat_days", "notify_before_expiry_days", "current_index",
                      "day_of_week", "day_of_month"):
            clean[key] = int(value) if value is not None else None
        elif key == "is_active":
            clean[key] = bool(value)
        elif key == "video_sequence":
            if isinstance(value, list):
                clean[key] = [int(v) for v in value if v is not None]
            else:
                clean[key] = []
        else:
            clean[key] = value
    return clean


# ---------------------------------------------------------------------------
# POST  /api/rotation/ar-content/{content_id}   — create or update
# ---------------------------------------------------------------------------

@router.post("/ar-content/{content_id}")
async def set_rotation(
    content_id: int,
    payload: Dict[str, Any],
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Create or update a rotation schedule for an AR content item."""
    _require_auth(current_user)
    clean = _sanitise_payload(payload)

    stmt = select(VideoRotationSchedule).where(
        VideoRotationSchedule.ar_content_id == content_id
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        for k, v in clean.items():
            if hasattr(existing, k):
                setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return {"id": existing.id, "status": "updated"}

    sched = VideoRotationSchedule(
        ar_content_id=content_id,
        rotation_type=clean.get("rotation_type", "fixed"),
        default_video_id=clean.get("default_video_id"),
        date_rules=clean.get("date_rules", []),
        video_sequence=clean.get("video_sequence", []),
        current_index=clean.get("current_index", 0),
        random_seed=clean.get("random_seed"),
        no_repeat_days=clean.get("no_repeat_days", 1),
        time_of_day=clean.get("time_of_day"),
        day_of_week=clean.get("day_of_week"),
        day_of_month=clean.get("day_of_month"),
        cron_expression=clean.get("cron_expression"),
        is_active=clean.get("is_active", True),
        notify_before_expiry_days=clean.get("notify_before_expiry_days", 7),
    )
    db.add(sched)
    await db.flush()
    await db.commit()
    await db.refresh(sched)
    return {"id": sched.id, "status": "created"}


# ---------------------------------------------------------------------------
# PUT  /api/rotation/{schedule_id}   — update existing
# ---------------------------------------------------------------------------

@router.put("/{schedule_id}")
async def update_rotation(
    schedule_id: int,
    payload: Dict[str, Any],
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing rotation schedule by id."""
    _require_auth(current_user)

    sched = await db.get(VideoRotationSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Rotation schedule not found")

    clean = _sanitise_payload(payload)
    for k, v in clean.items():
        if hasattr(sched, k):
            setattr(sched, k, v)

    await db.commit()
    await db.refresh(sched)
    return {"status": "updated", "id": sched.id}


# ---------------------------------------------------------------------------
# DELETE  /api/rotation/{schedule_id}
# ---------------------------------------------------------------------------

@router.delete("/{schedule_id}")
async def delete_rotation(
    schedule_id: int,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Delete a rotation schedule."""
    _require_auth(current_user)

    sched = await db.get(VideoRotationSchedule, schedule_id)
    if not sched:
        raise HTTPException(status_code=404, detail="Rotation schedule not found")

    await db.delete(sched)
    await db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# POST  /api/rotation/ar-content/{content_id}/sequence
# ---------------------------------------------------------------------------

@router.post("/ar-content/{content_id}/sequence")
async def set_rotation_sequence(
    content_id: int,
    payload: Dict[str, Any],
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Set or update the video sequence for a content's rotation schedule."""
    _require_auth(current_user)

    seq = payload.get("video_sequence")
    if not isinstance(seq, list) or not seq:
        raise HTTPException(
            status_code=400,
            detail="video_sequence must be a non-empty array of video IDs",
        )

    seq = [int(v) for v in seq if v is not None]

    res = await db.execute(
        select(VideoRotationSchedule).where(
            VideoRotationSchedule.ar_content_id == content_id
        )
    )
    sched = res.scalars().first()
    if not sched:
        sched = VideoRotationSchedule(
            ar_content_id=content_id,
            rotation_type="daily_cycle",
            video_sequence=seq,
            current_index=0,
            is_active=True,
        )
        db.add(sched)
    else:
        sched.video_sequence = seq
        sched.current_index = 0

    await db.commit()
    return {"status": "sequence_set", "count": len(seq)}


# ---------------------------------------------------------------------------
# GET  /api/rotation/ar-content/{content_id}/calendar
# ---------------------------------------------------------------------------

@router.get("/ar-content/{content_id}/calendar")
async def rotation_calendar(
    content_id: int,
    month: str,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Return a calendar of planned videos for the given month (YYYY-MM)."""
    _require_auth(current_user)

    import calendar as cal_mod
    from datetime import datetime

    from app.models.video import Video

    try:
        first_day = datetime.strptime(month + "-01", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM")

    days_in_month = cal_mod.monthrange(first_day.year, first_day.month)[1]

    vids_res = await db.execute(
        select(Video)
        .where(Video.ar_content_id == content_id)
        .order_by(Video.rotation_order.asc(), Video.id.asc())
    )
    vids = vids_res.scalars().all()

    sched_res = await db.execute(
        select(VideoRotationSchedule).where(
            VideoRotationSchedule.ar_content_id == content_id
        )
    )
    sched = sched_res.scalars().first()
    seq = sched.video_sequence if sched and sched.video_sequence else [v.id for v in vids]

    calendar_map = []
    for d in range(1, days_in_month + 1):
        day = first_day.replace(day=d)
        chosen = None
        for v in vids:
            if v.schedule_start and v.schedule_end and v.schedule_start <= day <= v.schedule_end:
                chosen = v
                break
        if not chosen and seq:
            idx = day.toordinal() % len(seq)
            vid_id = seq[idx]
            chosen = next((v for v in vids if v.id == vid_id), None)
        calendar_map.append({
            "date": day.strftime("%Y-%m-%d"),
            "video_id": chosen.id if chosen else None,
            "title": chosen.title if chosen else None,
        })
    return {"month": month, "days": calendar_map}
