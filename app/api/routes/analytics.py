from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct, text, and_
import structlog

from app.core.database import get_db
from app.models.ar_view_session import ARViewSession
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
from app.api.routes.alerts_ws import broadcast_analytics_event

router = APIRouter()
logger = structlog.get_logger()


@router.get("/analytics/overview")
async def analytics_overview(
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    content_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get analytics overview with optional filters.
    
    Args:
        company_id: Filter by company
        project_id: Filter by project
        content_id: Filter by AR content
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow() - timedelta(days=30)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow()
    
    # Build query conditions
    conditions = [ARViewSession.created_at >= start_dt, ARViewSession.created_at <= end_dt]
    
    if company_id:
        conditions.append(ARViewSession.company_id == company_id)
    if project_id:
        conditions.append(ARViewSession.project_id == project_id)
    if content_id:
        conditions.append(ARViewSession.ar_content_id == content_id)
    
    # Total views
    views_query = select(func.count()).select_from(ARViewSession).where(and_(*conditions))
    total_views_result = await db.execute(views_query)
    total_views = total_views_result.scalar() or 0
    
    # Unique sessions
    unique_sessions_query = select(func.count(distinct(ARViewSession.session_id))).where(and_(*conditions))
    unique_sessions_result = await db.execute(unique_sessions_query)
    unique_sessions = unique_sessions_result.scalar() or 0
    
    # Average session duration
    duration_query = select(func.avg(ARViewSession.duration_seconds)).where(and_(*conditions))
    duration_result = await db.execute(duration_query)
    avg_duration = duration_result.scalar() or 0
    
    # Average FPS
    fps_query = select(func.avg(ARViewSession.avg_fps)).where(and_(*conditions))
    fps_result = await db.execute(fps_query)
    avg_fps = fps_result.scalar() or 0
    
    # Successful tracking rate
    tracking_conditions = conditions + [ARViewSession.tracking_quality == "good"]
    tracking_query = select(func.count()).select_from(ARViewSession).where(and_(*tracking_conditions))
    tracking_result = await db.execute(tracking_query)
    successful_tracking = tracking_result.scalar() or 0
    tracking_rate = (successful_tracking / total_views * 100) if total_views > 0 else 0
    
    # Active content
    active_content_conditions = [ARContent.is_active == True]
    if company_id:
        active_content_conditions.append(ARContent.company_id == company_id)
    if project_id:
        active_content_conditions.append(ARContent.project_id == project_id)
        
    active_content_query = select(func.count()).select_from(ARContent).where(and_(*active_content_conditions))
    active_content_result = await db.execute(active_content_query)
    active_content = active_content_result.scalar() or 0
    
    return {
        "total_views": total_views,
        "unique_sessions": unique_sessions,
        "avg_session_duration": round(avg_duration, 2),
        "avg_fps": round(avg_fps, 2),
        "tracking_success_rate": round(tracking_rate, 2),
        "active_content": active_content,
        "date_range": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        }
    }


@router.get("/analytics/trends")
async def analytics_trends(
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    content_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    interval: str = "day",  # day, week, month
    db: AsyncSession = Depends(get_db)
):
    """
    Get trend data for analytics.
    
    Args:
        company_id: Filter by company
        project_id: Filter by project
        content_id: Filter by AR content
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Time interval (day, week, month)
    """
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow() - timedelta(days=30)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow()
    
    # Build query conditions
    conditions = [ARViewSession.created_at >= start_dt, ARViewSession.created_at <= end_dt]
    
    if company_id:
        conditions.append(ARViewSession.company_id == company_id)
    if project_id:
        conditions.append(ARViewSession.project_id == project_id)
    if content_id:
        conditions.append(ARViewSession.ar_content_id == content_id)
    
    # Group by date
    if interval == "day":
        date_trunc = "day"
    elif interval == "week":
        date_trunc = "week"
    else:
        date_trunc = "month"
    
    # Views by date
    views_query = select(
        func.date_trunc(date_trunc, ARViewSession.created_at).label('date'),
        func.count().label('views')
    ).where(and_(*conditions)).group_by(func.date_trunc(date_trunc, ARViewSession.created_at)).order_by(text('date'))
    
    views_result = await db.execute(views_query)
    views_data = [{"date": row[0].isoformat(), "views": row[1]} for row in views_result.fetchall()]
    
    # Average duration by date
    duration_query = select(
        func.date_trunc(date_trunc, ARViewSession.created_at).label('date'),
        func.avg(ARViewSession.duration_seconds).label('avg_duration')
    ).where(and_(*conditions)).group_by(func.date_trunc(date_trunc, ARViewSession.created_at)).order_by(text('date'))
    
    duration_result = await db.execute(duration_query)
    duration_data = [{"date": row[0].isoformat(), "avg_duration": round(row[1] or 0, 2)} for row in duration_result.fetchall()]
    
    return {
        "views_trend": views_data,
        "duration_trend": duration_data,
        "interval": interval
    }


@router.get("/analytics/top-content")
async def top_content(
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get top AR content by views.
    
    Args:
        company_id: Filter by company
        project_id: Filter by project
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Number of items to return
    """
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow() - timedelta(days=30)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow()
    
    # Build query conditions
    conditions = [ARViewSession.created_at >= start_dt, ARViewSession.created_at <= end_dt]
    
    if company_id:
        conditions.append(ARViewSession.company_id == company_id)
    if project_id:
        conditions.append(ARViewSession.project_id == project_id)
    
    # Join with ARContent to get content details
    top_query = select(
        ARContent.id,
        ARContent.title,
        func.count(ARViewSession.id).label('views'),
        func.avg(ARViewSession.duration_seconds).label('avg_duration')
    ).join(ARContent, ARViewSession.ar_content_id == ARContent.id).where(and_(*conditions)).group_by(
        ARContent.id, ARContent.title
    ).order_by(text('views DESC')).limit(limit)
    
    top_result = await db.execute(top_query)
    top_content = [{
        "id": row[0],
        "title": row[1],
        "views": row[2],
        "avg_duration": round(row[3] or 0, 2)
    } for row in top_result.fetchall()]
    
    return top_content


@router.get("/analytics/device-stats")
async def device_stats(
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    content_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get device and browser statistics.
    
    Args:
        company_id: Filter by company
        project_id: Filter by project
        content_id: Filter by AR content
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow() - timedelta(days=30)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow()
    
    # Build query conditions
    conditions = [ARViewSession.created_at >= start_dt, ARViewSession.created_at <= end_dt]
    
    if company_id:
        conditions.append(ARViewSession.company_id == company_id)
    if project_id:
        conditions.append(ARViewSession.project_id == project_id)
    if content_id:
        conditions.append(ARViewSession.ar_content_id == content_id)
    
    # Device type distribution
    device_query = select(
        ARViewSession.device_type,
        func.count().label('count')
    ).where(and_(*conditions)).group_by(ARViewSession.device_type)
    
    device_result = await db.execute(device_query)
    device_stats = [{"device_type": row[0] or "Unknown", "count": row[1]} for row in device_result.fetchall()]
    
    # Browser distribution
    browser_query = select(
        ARViewSession.browser,
        func.count().label('count')
    ).where(and_(*conditions)).group_by(ARViewSession.browser)
    
    browser_result = await db.execute(browser_query)
    browser_stats = [{"browser": row[0] or "Unknown", "count": row[1]} for row in browser_result.fetchall()]
    
    # FPS by device
    fps_query = select(
        ARViewSession.device_type,
        func.avg(ARViewSession.avg_fps).label('avg_fps')
    ).where(and_(*conditions)).group_by(ARViewSession.device_type)
    
    fps_result = await db.execute(fps_query)
    fps_stats = [{"device_type": row[0] or "Unknown", "avg_fps": round(row[1] or 0, 2)} for row in fps_result.fetchall()]
    
    return {
        "device_distribution": device_stats,
        "browser_distribution": browser_stats,
        "fps_by_device": fps_stats
    }


@router.get("/analytics/engagement")
async def engagement_metrics(
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get engagement metrics.
    
    Args:
        company_id: Filter by company
        project_id: Filter by project
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    # Parse dates
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow() - timedelta(days=30)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow()
    
    # Build query conditions
    conditions = [ARViewSession.created_at >= start_dt, ARViewSession.created_at <= end_dt]
    
    if company_id:
        conditions.append(ARViewSession.company_id == company_id)
    if project_id:
        conditions.append(ARViewSession.project_id == project_id)
    
    # First session duration
    # This is a simplified approach - in reality, you'd need to identify first sessions per user
    first_session_query = select(func.avg(ARViewSession.duration_seconds)).where(and_(*conditions))
    first_session_result = await db.execute(first_session_query)
    avg_first_session_duration = first_session_result.scalar() or 0
    
    # Session frequency (sessions per user)
    sessions_per_user_query = select(
        ARViewSession.session_id,
        func.count().label('session_count')
    ).where(and_(*conditions)).group_by(ARViewSession.session_id)
    
    sessions_per_user_result = await db.execute(sessions_per_user_query)
    session_counts = [row[1] for row in sessions_per_user_result.fetchall()]
    avg_sessions_per_user = sum(session_counts) / len(session_counts) if session_counts else 0
    
    # Time of day heatmap (simplified - by hour)
    hour_query = select(
        func.extract('hour', ARViewSession.created_at).label('hour'),
        func.count().label('count')
    ).where(and_(*conditions)).group_by(text('hour')).order_by(text('hour'))
    
    hour_result = await db.execute(hour_query)
    hourly_data = [{"hour": int(row[0]), "count": row[1]} for row in hour_result.fetchall()]
    
    return {
        "avg_first_session_duration": round(avg_first_session_duration, 2),
        "avg_sessions_per_user": round(avg_sessions_per_user, 2),
        "hourly_distribution": hourly_data
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
        duration_seconds=payload.get("duration_seconds"),
        avg_fps=payload.get("avg_fps"),
        tracking_quality=payload.get("tracking_quality"),
        video_played=bool(payload.get("video_played")),
    )
    db.add(s)
    await db.commit()
    
    # Broadcast analytics event
    event_data = {
        "event_type": "ar_session_created",
        "ar_content_id": ar_content_id,
        "company_id": company_id,
        "project_id": project_id,
        "device_type": payload.get("device_type"),
        "browser": payload.get("browser"),
        "duration_seconds": payload.get("duration_seconds"),
        "avg_fps": payload.get("avg_fps"),
        "tracking_quality": payload.get("tracking_quality"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await broadcast_analytics_event(event_data, company_id)
    
    logger.info("ar_session_tracked", 
                ar_content_id=ar_content_id, 
                company_id=company_id, 
                duration=payload.get("duration_seconds"))
    
    return {"status": "tracked"}