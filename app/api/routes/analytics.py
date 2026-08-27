from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import os
import shutil
import structlog
import time
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, text

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_view_session import ARViewSession
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
from app.models.user import User
from app.api.deps_authz import require_company_access
from app.api.routes.auth import get_current_active_user

router = APIRouter()


def _utcnow_naive() -> datetime:
    """Return UTC now as naive datetime for DB comparisons."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_storage_used_gb() -> float:
    try:
        base_path = Path(settings.STORAGE_BASE_PATH)
        if not base_path.exists() or not base_path.is_dir():
            return 0.0
        usage = shutil.disk_usage(base_path)
        return round(usage.used / (1024 ** 3), 2)
    except Exception:
        return 0.0


def compute_uptime() -> float | None:
    try:
        import psutil
        boot_time = time.time() - psutil.boot_time()
        return round(boot_time / 3600, 1)
    except Exception:
        return None


@router.get("/overview")
async def analytics_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    since = _utcnow_naive() - timedelta(days=30)

    company_filter = None
    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        company_filter = getattr(current_user, 'company_id', None)

    total_views = await db.execute(
        select(func.count()).select_from(ARViewSession).where(ARViewSession.created_at >= since)
    )
    total_views_count = total_views.scalar() or 0

    if company_filter is not None:
        total_views = await db.execute(
            select(func.count()).select_from(ARViewSession).where(
                ARViewSession.created_at >= since,
                ARViewSession.company_id == company_filter,
            )
        )
        total_views_count = total_views.scalar() or 0

    try:
        unique_sessions = await db.execute(
            select(func.count(text('DISTINCT session_id'))).select_from(ARViewSession).where(ARViewSession.created_at >= since)
        )
    except Exception:
        unique_sessions = await db.execute(select(func.count(distinct(ARViewSession.session_id))).where(ARViewSession.created_at >= since))
    unique_sessions_count = unique_sessions.scalar() or 0

    if company_filter is not None:
        try:
            unique_sessions = await db.execute(
                select(func.count(text('DISTINCT session_id'))).select_from(ARViewSession).where(
                    ARViewSession.created_at >= since,
                    ARViewSession.company_id == company_filter,
                )
            )
        except Exception:
            unique_sessions = await db.execute(select(func.count(distinct(ARViewSession.session_id))).where(
                ARViewSession.created_at >= since,
                ARViewSession.company_id == company_filter,
            ))
        unique_sessions_count = unique_sessions.scalar() or 0

    active_content_stmt = select(func.count()).select_from(ARContent).where(ARContent.status == "active")
    if company_filter is not None:
        active_content_stmt = active_content_stmt.where(ARContent.company_id == company_filter)
    active_content = await db.execute(active_content_stmt)
    active_content_count = active_content.scalar() or 0

    active_companies_stmt = select(func.count()).select_from(Company).where(Company.status == "active")
    if company_filter is not None:
        active_companies_stmt = active_companies_stmt.where(Company.id == company_filter)
    active_companies = await db.execute(active_companies_stmt)
    active_companies_count = active_companies.scalar() or 0

    active_projects_stmt = select(func.count()).select_from(Project).where(Project.status == "active")
    if company_filter is not None:
        active_projects_stmt = active_projects_stmt.where(Project.company_id == company_filter)
    active_projects = await db.execute(active_projects_stmt)
    active_projects_count = active_projects.scalar() or 0
    
    storage_used_gb = compute_storage_used_gb()
    revenue = 0.0
    uptime = compute_uptime()
    
    return {
        "total_views": total_views_count,
        "unique_sessions": unique_sessions_count,
        "active_content": active_content_count,
        "storage_used_gb": storage_used_gb,
        "active_companies": active_companies_count,
        "active_projects": active_projects_count,
        "revenue": revenue,
        "uptime": uptime,
    }


@router.get("/summary")
async def analytics_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await analytics_overview(request=request, db=db, current_user=current_user)


@router.get("/companies/{company_id}")
async def analytics_company(
    company_id: int,
    request: Request,
    company: Company = Depends(require_company_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    since = _utcnow_naive() - timedelta(days=30)
    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.company_id == company_id, ARViewSession.created_at >= since))
    return {"company_id": company_id, "views_30_days": views.scalar() or 0}


@router.get("/company/{company_id}")
async def analytics_company_alias(
    company_id: int,
    request: Request,
    company: Company = Depends(require_company_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await analytics_company(company_id, db)


@router.get("/projects/{project_id}")
async def analytics_project(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    since = _utcnow_naive() - timedelta(days=30)
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if project.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this project")

    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.project_id == project_id, ARViewSession.created_at >= since))
    return {"project_id": project_id, "views_30_days": views.scalar() or 0}


@router.get("/ar-content/{content_id}")
async def analytics_content(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    since = _utcnow_naive() - timedelta(days=30)
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")

    views = await db.execute(select(func.count()).select_from(ARViewSession).where(ARViewSession.ar_content_id == content_id, ARViewSession.created_at >= since))
    return {"ar_content_id": content_id, "views_30_days": views.scalar() or 0}


@router.get("/content/{content_id}")
async def analytics_content_alias(
    content_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Backward-compatible alias for older admin/frontend clients."""
    return await analytics_content(content_id=content_id, request=request, db=db, current_user=current_user)


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
