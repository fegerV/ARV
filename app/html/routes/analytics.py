"""HTML route for the analytics dashboard.

Provides summary cards, time-series views data, top content,
per-company breakdown, device / browser distribution, average session
duration and video play rate.  All queries accept a configurable
``period`` parameter (7 / 30 / 90 / 0 = all-time).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import cast, Date, case, distinct, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user_optional
from app.html.deps import get_html_db
from app.html.filters import datetime_format, tojson_filter
from app.models.ar_content import ARContent
from app.models.ar_view_session import ARViewSession
from app.models.company import Company
from app.models.project import Project

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
templates.env.filters["datetime_format"] = datetime_format
templates.env.filters["tojson"] = tojson_filter

# Valid period values (days).  0 means "all time".
_VALID_PERIODS = {7, 30, 90, 0}
_DEFAULT_PERIOD = 30


# ------------------------------------------------------------------
# Data helpers
# ------------------------------------------------------------------

def _empty_analytics() -> dict[str, Any]:
    """Return a safe empty-state analytics dict."""
    return {
        "period": _DEFAULT_PERIOD,
        "total_views": 0,
        "unique_sessions": 0,
        "active_content": 0,
        "total_content": 0,
        "active_companies": 0,
        "active_projects": 0,
        "avg_duration": 0,
        "video_play_rate": 0,
        "views_by_day": [],
        "top_content": [],
        "company_stats": [],
        "device_stats": [],
        "browser_stats": [],
    }


async def get_analytics_data(db: AsyncSession, period: int = _DEFAULT_PERIOD) -> dict[str, Any]:
    """Collect all analytics data for the dashboard.

    Args:
        db: Async database session.
        period: Number of days to look back (0 = all time).

    Returns:
        Dictionary ready to be passed into the Jinja2 template context.
    """
    try:
        # Use naive UTC to match the column type (DateTime without timezone)
        now = datetime.utcnow()
        since = now - timedelta(days=period) if period > 0 else None

        def _time_filter(stmt):
            """Append a ``created_at >= since`` clause when a period is set."""
            if since is not None:
                return stmt.where(ARViewSession.created_at >= since)
            return stmt

        # --- Summary counts (total_views first — fallback depends on it) -------
        total_views = (
            await db.execute(
                _time_filter(select(func.count()).select_from(ARViewSession))
            )
        ).scalar() or 0
        if total_views == 0:
            total_views = (
                await db.execute(
                    select(func.coalesce(func.sum(ARContent.views_count), 0))
                )
            ).scalar() or 0

        # AsyncSession не поддерживает параллельные операции — выполняем запросы последовательно.
        _r = await db.execute(
            _time_filter(
                select(func.count(distinct(ARViewSession.session_id))).select_from(ARViewSession)
            )
        )
        unique_sessions = _r.scalar() or 0
        _r = await db.execute(
            select(func.count()).select_from(ARContent).where(
                ARContent.status.in_(["ready", "active"])
            )
        )
        active_content = _r.scalar() or 0
        _r = await db.execute(select(func.count()).select_from(ARContent))
        total_content = _r.scalar() or 0
        _r = await db.execute(
            select(func.count()).select_from(Company).where(Company.status == "active")
        )
        active_companies = _r.scalar() or 0
        _r = await db.execute(
            select(func.count()).select_from(Project).where(Project.status == "active")
        )
        active_projects = _r.scalar() or 0
        _r = await db.execute(
            _time_filter(
                select(func.avg(ARViewSession.duration_seconds)).select_from(ARViewSession)
            )
        )
        v = _r.scalar()
        avg_duration = round(float(v), 1) if v is not None else 0
        _r = await db.execute(_time_filter(select(func.count()).select_from(ARViewSession)))
        video_total = _r.scalar() or 0
        _r = await db.execute(
            _time_filter(
                select(func.count()).select_from(ARViewSession).where(
                    ARViewSession.video_played.is_(True)
                )
            )
        )
        video_played = _r.scalar() or 0
        views_day_rows = await db.execute(
            _time_filter(
                select(
                    cast(ARViewSession.created_at, Date).label("day"),
                    func.count().label("cnt"),
                )
                .select_from(ARViewSession)
                .group_by(cast(ARViewSession.created_at, Date))
                .order_by(cast(ARViewSession.created_at, Date))
            )
        )
        top_rows = await db.execute(
            _time_filter(
                select(
                    ARViewSession.ar_content_id,
                    func.count().label("views"),
                )
                .select_from(ARViewSession)
                .group_by(ARViewSession.ar_content_id)
                .order_by(func.count().desc())
                .limit(10)
            )
        )
        company_rows = await db.execute(
            _time_filter(
                select(
                    ARViewSession.company_id,
                    func.count().label("views"),
                    func.count(distinct(ARViewSession.session_id)).label("sessions"),
                    func.avg(ARViewSession.duration_seconds).label("avg_dur"),
                    func.sum(
                        case(
                            (ARViewSession.video_played.is_(True), 1),
                            else_=0,
                        )
                    ).label("vp_count"),
                )
                .select_from(ARViewSession)
                .group_by(ARViewSession.company_id)
                .order_by(func.count().desc())
            )
        )
        device_rows = await db.execute(
            _time_filter(
                select(
                    func.coalesce(ARViewSession.device_type, literal_column("'unknown'")).label("dtype"),
                    func.count().label("cnt"),
                )
                .select_from(ARViewSession)
                .group_by(func.coalesce(ARViewSession.device_type, literal_column("'unknown'")))
                .order_by(func.count().desc())
            )
        )
        browser_rows = await db.execute(
            _time_filter(
                select(
                    func.coalesce(ARViewSession.browser, literal_column("'unknown'")).label("bname"),
                    func.count().label("cnt"),
                )
                .select_from(ARViewSession)
                .group_by(func.coalesce(ARViewSession.browser, literal_column("'unknown'")))
                .order_by(func.count().desc())
                .limit(8)
            )
        )

        try:
            unique_sessions = int(unique_sessions)
        except (TypeError, ValueError):
            unique_sessions = int(total_views * 0.7) if total_views else 0
        if unique_sessions == 0 and total_views > 0:
            unique_sessions = total_views

        video_play_rate = (
            round(int(video_played) / int(video_total) * 100, 1) if video_total and int(video_total) > 0 else 0
        )

        views_day_rows = views_day_rows.all()
        top_rows = top_rows.all()
        company_rows = company_rows.all()
        device_rows = device_rows.all()
        browser_rows = browser_rows.all()

        # --- Views by day (time-series, from parallel result) ------------------
        # Build a continuous date range so the chart has no gaps
        days_count = period if period > 0 else (
            (now.date() - views_day_rows[0][0]).days + 1 if views_day_rows else 30
        )
        date_map: dict[str, int] = {str(row[0]): row[1] for row in views_day_rows}
        views_by_day: list[dict[str, Any]] = []
        for i in range(days_count):
            d = (now - timedelta(days=days_count - 1 - i)).date()
            views_by_day.append({"date": str(d), "views": date_map.get(str(d), 0)})

        # --- Top-10 content (from parallel result) -----------------------------
        top_content: list[dict[str, Any]] = []
        if top_rows:
            content_ids = [r[0] for r in top_rows]
            content_map_q = (
                select(
                    ARContent.id,
                    ARContent.order_number,
                    Company.name.label("company_name"),
                )
                .join(Company, ARContent.company_id == Company.id, isouter=True)
                .where(ARContent.id.in_(content_ids))
            )
            content_rows = (await db.execute(content_map_q)).all()
            info_map = {r[0]: (r[1], r[2]) for r in content_rows}
            for cid, views in top_rows:
                order_number, company_name = info_map.get(cid, (f"#{cid}", "—"))
                top_content.append({
                    "id": cid,
                    "order_number": order_number or f"#{cid}",
                    "company_name": company_name or "—",
                    "views": views,
                })
        else:
            # Fallback: use views_count from ARContent when no sessions recorded
            fallback_top_q = (
                select(
                    ARContent.id,
                    ARContent.order_number,
                    ARContent.views_count,
                    Company.name.label("company_name"),
                )
                .join(Company, ARContent.company_id == Company.id, isouter=True)
                .where(ARContent.views_count > 0)
                .order_by(ARContent.views_count.desc())
                .limit(10)
            )
            fallback_rows = (await db.execute(fallback_top_q)).all()
            for row in fallback_rows:
                top_content.append({
                    "id": row[0],
                    "order_number": row[1] or f"#{row[0]}",
                    "company_name": row[3] or "—",
                    "views": row[2] or 0,
                })

        # --- Company stats (from parallel result) ------------------------------
        company_stats: list[dict[str, Any]] = []
        if company_rows:
            cids = [r[0] for r in company_rows]
            cname_q = select(Company.id, Company.name).where(Company.id.in_(cids))
            cname_rows = (await db.execute(cname_q)).all()
            cname_map = {r[0]: r[1] for r in cname_rows}
            for cid, views, sessions, avg_d, vp in company_rows:
                vp_rate = round(int(vp or 0) / views * 100, 1) if views else 0
                company_stats.append({
                    "id": cid,
                    "name": cname_map.get(cid, f"Company #{cid}"),
                    "views": views,
                    "sessions": sessions,
                    "avg_duration": round(float(avg_d), 1) if avg_d else 0,
                    "video_rate": vp_rate,
                })
        else:
            # Fallback: aggregate views_count per company from ARContent
            fallback_cq = (
                select(
                    ARContent.company_id,
                    func.coalesce(func.sum(ARContent.views_count), 0).label("views"),
                    Company.name.label("cname"),
                )
                .join(Company, ARContent.company_id == Company.id, isouter=True)
                .group_by(ARContent.company_id, Company.name)
                .having(func.sum(ARContent.views_count) > 0)
                .order_by(func.sum(ARContent.views_count).desc())
            )
            fallback_crows = (await db.execute(fallback_cq)).all()
            for cid, views, cname in fallback_crows:
                company_stats.append({
                    "id": cid,
                    "name": cname or f"Company #{cid}",
                    "views": int(views),
                    "sessions": int(views),
                    "avg_duration": 0,
                    "video_rate": 0,
                })

        # --- Device & browser (from parallel result) ---------------------------
        device_stats = [{"label": r[0] or "unknown", "value": r[1]} for r in device_rows]
        browser_stats = [{"label": r[0] or "unknown", "value": r[1]} for r in browser_rows]

        return {
            "period": period,
            "total_views": total_views,
            "unique_sessions": unique_sessions,
            "active_content": active_content,
            "total_content": total_content,
            "active_companies": active_companies,
            "active_projects": active_projects,
            "avg_duration": avg_duration,
            "video_play_rate": video_play_rate,
            "views_by_day": views_by_day,
            "top_content": top_content,
            "company_stats": company_stats,
            "device_stats": device_stats,
            "browser_stats": browser_stats,
        }
    except Exception as exc:
        logger.error("error_getting_analytics", error=str(exc), exc_info=True)
        data = _empty_analytics()
        data["period"] = period
        return data


# ------------------------------------------------------------------
# Route
# ------------------------------------------------------------------

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=Depends(get_current_user_optional),
):
    """Analytics dashboard page."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)

    # Parse period from query params
    try:
        period = int(request.query_params.get("period", _DEFAULT_PERIOD))
    except (TypeError, ValueError):
        period = _DEFAULT_PERIOD
    if period not in _VALID_PERIODS:
        period = _DEFAULT_PERIOD

    try:
        analytics_data = await get_analytics_data(db, period=period)
    except Exception as exc:
        logger.error("analytics_page_error", error=str(exc))
        analytics_data = _empty_analytics()
        analytics_data["period"] = period

    context = {
        "request": request,
        "analytics_data": analytics_data,
        "current_user": current_user,
    }
    return templates.TemplateResponse("analytics.html", context)
