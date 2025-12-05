from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

from app.core.database import get_db
from app.models.ar_view_session import ARViewSession
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company

router = APIRouter()


@router.get("/analytics/overview")
async def analytics_overview(db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    total_views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.created_at >= since))
    total_views_count = total_views.scalar() or 0
    unique_sessions = await db.execute(select(func.count(distinct(ARViewSession.session_id))).where(ARViewSession.created_at >= since))
    unique_sessions_count = unique_sessions.scalar() or 0
    active_content = await db.execute(select(func.count()).select_from(ARContent).where(ARContent.is_active == True))
    active_content_count = active_content.scalar() or 0
    # Storage used is placeholder; can be computed per company later
    return {
        "total_views": total_views_count,
        "unique_sessions": unique_sessions_count,
        "active_content": active_content_count,
        "storage_used_gb": None,
    }


@router.get("/analytics/companies/{company_id}")
async def analytics_company(company_id: int, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.company_id == company_id, ARViewSession.created_at >= since))
    return {"company_id": company_id, "views_30_days": views.scalar() or 0}


@router.get("/analytics/projects/{project_id}")
async def analytics_project(project_id: int, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.project_id == project_id, ARViewSession.created_at >= since))
    return {"project_id": project_id, "views_30_days": views.scalar() or 0}


@router.get("/analytics/ar-content/{content_id}")
async def analytics_content(content_id: int, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.ar_content_id == content_id, ARViewSession.created_at >= since))
    return {"ar_content_id": content_id, "views_30_days": views.scalar() or 0}


@router.post("/analytics/ar-session")
async def track_ar_session(payload: dict, db: AsyncSession = Depends(get_db)):
    # Accept portrait_id as unique_id for ARContent (from viewer), or ar_content_id
    unique_id: Optional[str] = payload.get("portrait_id") or payload.get("ar_content_unique_id")
    ar_content_id: Optional[int] = payload.get("ar_content_id")
    company_id: Optional[int] = None
    project_id: Optional[int] = None

    if unique_id and not ar_content_id:
        stmt = select(ARContent).where(ARContent.unique_id == unique_id)
        res = await db.execute(stmt)
        ac = res.scalar_one_or_none()
        if ac:
            ar_content_id = ac.id
            company_id = ac.company_id
            project_id = ac.project_id
    elif ar_content_id:
        ac = await db.get(ARContent, ar_content_id)
        if ac:
            company_id = ac.company_id
            project_id = ac.project_id

    s = ARViewSession(
        ar_content_id=ar_content_id or 0,
        project_id=project_id or 0,
        company_id=company_id or 0,
        session_id=payload.get("session_id"),
        user_agent=payload.get("user_agent"),
        device_type=payload.get("device_type"),
        browser=payload.get("browser"),
        os=payload.get("os"),
        duration_seconds=None,
        tracking_quality=payload.get("tracking_quality"),
        video_played=bool(payload.get("video_played")),
    )
    db.add(s)
    await db.commit()
    return {"status": "tracked"}
