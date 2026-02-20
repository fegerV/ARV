from datetime import datetime, timedelta
from typing import Optional
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, text

from app.core.database import get_db
from app.models.ar_view_session import ARViewSession
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company

router = APIRouter()


@router.get("/overview")
async def analytics_overview(db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    
    # Use text() for SQLite compatibility with count(distinct)
    total_views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.created_at >= since))
    total_views_count = total_views.scalar() or 0
    
    # For SQLite compatibility, use a different approach for distinct count
    try:
        unique_sessions = await db.execute(
            select(func.count(text('DISTINCT session_id'))).select_from(ARViewSession).where(ARViewSession.created_at >= since)
        )
    except Exception:
        # Fallback for PostgreSQL
        unique_sessions = await db.execute(select(func.count(distinct(ARViewSession.session_id))).where(ARViewSession.created_at >= since))
    unique_sessions_count = unique_sessions.scalar() or 0
    
    active_content = await db.execute(select(func.count()).select_from(ARContent).where(ARContent.status == "active"))
    active_content_count = active_content.scalar() or 0
    
    # Get active companies and projects
    active_companies = await db.execute(select(func.count()).select_from(Company).where(Company.status == "active"))
    active_companies_count = active_companies.scalar() or 0
    
    active_projects = await db.execute(select(func.count()).select_from(Project).where(Project.status == "active"))
    active_projects_count = active_projects.scalar() or 0
    
    # Placeholder values for revenue and uptime
    revenue = "$0.00"
    uptime = "99.9%"
    
    # Storage used is placeholder; can be computed per company later
    return {
        "total_views": total_views_count,
        "unique_sessions": unique_sessions_count,
        "active_content": active_content_count,
        "storage_used_gb": 0,
        "active_companies": active_companies_count,
        "active_projects": active_projects_count,
        "revenue": revenue,
        "uptime": uptime,
    }


@router.get("/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db)):
    return await analytics_overview(db)


@router.get("/companies/{company_id}")
async def analytics_company(company_id: int, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.company_id == company_id, ARViewSession.created_at >= since))
    return {"company_id": company_id, "views_30_days": views.scalar() or 0}


@router.get("/company/{company_id}")
async def analytics_company_alias(company_id: int, db: AsyncSession = Depends(get_db)):
    return await analytics_company(company_id, db)


@router.get("/projects/{project_id}")
async def analytics_project(project_id: int, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.project_id == project_id, ARViewSession.created_at >= since))
    return {"project_id": project_id, "views_30_days": views.scalar() or 0}


@router.get("/ar-content/{content_id}")
async def analytics_content(content_id: int, db: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.ar_content_id == content_id, ARViewSession.created_at >= since))
    return {"ar_content_id": content_id, "views_30_days": views.scalar() or 0}


@router.post("/ar-session")
async def track_ar_session(payload: dict, db: AsyncSession = Depends(get_db)):
    """Legacy endpoint kept for compatibility.

    IMPORTANT: ARViewSession uses UUID FK fields; do not write sentinel 0 values.
    """
    unique_id: Optional[str] = payload.get("ar_content_unique_id") or payload.get("portrait_id")
    session_id_raw: Optional[str] = payload.get("session_id")

    if not unique_id:
        raise HTTPException(status_code=400, detail="ar_content_unique_id is required")
    if not session_id_raw:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        session_uuid = uuid.UUID(str(session_id_raw))
    except Exception:
        raise HTTPException(status_code=400, detail="session_id must be UUID")

    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")

    s = ARViewSession(
        ar_content_id=ac.id,
        project_id=ac.project_id,
        company_id=ac.company_id,
        session_id=str(session_uuid),  # Store UUID as string for SQLite compatibility
        user_agent=payload.get("user_agent"),
        device_type=payload.get("device_type"),
        device_model=payload.get("device_model"),
        browser=payload.get("browser"),
        os=payload.get("os"),
        duration_seconds=payload.get("duration_seconds"),
        tracking_quality=payload.get("tracking_quality"),
        video_played=bool(payload.get("video_played")),
    )
    db.add(s)
    await db.commit()
    return {"status": "tracked", "session_id": str(session_uuid)}


@router.post("/mobile/sessions")
async def mobile_session_start(payload: dict, db: AsyncSession = Depends(get_db)):
    """Create AR mobile/browser session (minimal REST)."""
    unique_id: Optional[str] = payload.get("ar_content_unique_id")
    session_id_raw: Optional[str] = payload.get("session_id")

    if not unique_id:
        raise HTTPException(status_code=400, detail="ar_content_unique_id is required")
    if not session_id_raw:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        session_uuid = uuid.UUID(str(session_id_raw))
    except Exception:
        raise HTTPException(status_code=400, detail="session_id must be UUID")

    res = await db.execute(select(ARContent).where(ARContent.unique_id == unique_id))
    ac = res.scalar_one_or_none()
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")

    # idempotency: do not create duplicates for same session_id
    existing = await db.execute(select(ARViewSession).where(ARViewSession.session_id == str(session_uuid)))
    if existing.scalar_one_or_none():
        return {"status": "exists", "session_id": str(session_uuid)}

    s = ARViewSession(
        ar_content_id=ac.id,
        project_id=ac.project_id,
        company_id=ac.company_id,
        session_id=str(session_uuid),  # Store UUID as string for SQLite compatibility
        user_agent=payload.get("user_agent"),
        device_type=payload.get("device_type"),
        device_model=payload.get("device_model"),
        browser=payload.get("browser"),
        os=payload.get("os"),
        ip_address=payload.get("ip_address"),
        duration_seconds=None,
        tracking_quality=payload.get("tracking_quality"),
        video_played=bool(payload.get("video_played")),
    )
    db.add(s)
    await db.commit()
    return {"status": "created", "session_id": str(session_uuid)}


@router.post("/ar-diagnostic")
async def ar_diagnostic_event(payload: dict):
    """Приём диагностических событий AR (тайминги, этапы) при открытии viewer с ?diagnose=1.
    Логирует события для анализа зависаний на мобильных (MindAR start, _startVideo, _startAR и т.д.).
    """
    logger = structlog.get_logger()
    stage = payload.get("event") or payload.get("stage")
    duration_ms = payload.get("duration_ms")
    user_agent = payload.get("user_agent", "")
    ar_content_unique_id = payload.get("ar_content_unique_id", "")
    err = payload.get("error")
    logger.info(
        "ar_diagnostic",
        stage=stage,
        duration_ms=duration_ms,
        user_agent=user_agent[:200] if user_agent else None,
        ar_content_unique_id=ar_content_unique_id or None,
        error=err,
    )
    return {"status": "ok"}


@router.post("/mobile/analytics")
async def mobile_analytics_update(payload: dict, db: AsyncSession = Depends(get_db)):
    """Update session analytics (minimal REST)."""
    session_id_raw: Optional[str] = payload.get("session_id")
    if not session_id_raw:
        raise HTTPException(status_code=400, detail="session_id is required")

    try:
        session_uuid = uuid.UUID(str(session_id_raw))
    except Exception:
        raise HTTPException(status_code=400, detail="session_id must be UUID")

    res = await db.execute(select(ARViewSession).where(ARViewSession.session_id == str(session_uuid)))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")

    if "duration_seconds" in payload:
        s.duration_seconds = payload.get("duration_seconds")
    if "tracking_quality" in payload:
        s.tracking_quality = payload.get("tracking_quality")
    if "video_played" in payload:
        s.video_played = bool(payload.get("video_played"))

    await db.commit()
    return {"status": "updated", "session_id": str(session_uuid)}
