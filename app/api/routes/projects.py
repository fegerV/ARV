from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.project import Project
from app.models.company import Company

router = APIRouter()


@router.post("/projects")
async def create_project(payload: dict, db: AsyncSession = Depends(get_db)):
    required = ["company_id", "name", "slug"]
    for r in required:
        if r not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {r}")

    proj = Project(
        company_id=payload["company_id"],
        name=payload["name"],
        slug=payload["slug"],
        folder_path=payload.get("folder_path"),
        description=payload.get("description"),
        project_type=payload.get("project_type"),
        subscription_type=payload.get("subscription_type", "monthly"),
        starts_at=_parse_dt(payload.get("starts_at")),
        expires_at=_parse_dt(payload.get("expires_at")),
        auto_renew=1 if payload.get("auto_renew") else 0,
        status=payload.get("status", "active"),
        notify_before_expiry_days=payload.get("notify_before_expiry_days", 7),
        tags=_parse_tags(payload.get("tags")),
    )
    db.add(proj)
    await db.flush()
    await db.commit()
    await db.refresh(proj)
    return {"id": proj.id, "slug": proj.slug}

@router.post("/companies/{company_id}/projects")
async def create_project_for_company(company_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    payload = {**payload, "company_id": company_id}
    return await create_project(payload, db)
    stmt = select(Project).where(Project.company_id == company_id)
    res = await db.execute(stmt)
    projects = res.scalars().all()
    items = []
    now = datetime.utcnow()
    for p in projects:
        days_left = None
        if p.expires_at:
            delta = p.expires_at - now
            days_left = max(0, delta.days)
        items.append({
            "id": p.id,
            "name": p.name,
            "slug": p.slug,
            "status": p.status,
            "period": {
                "starts_at": _iso(p.starts_at),
                "expires_at": _iso(p.expires_at),
                "days_left": days_left,
            },
            "folder_path": p.folder_path,
            "project_type": p.project_type,
        })
    return {"projects": items}


@router.put("/projects/{project_id}")
async def update_project(project_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    for k, v in payload.items():
        if hasattr(proj, k):
            setattr(proj, k, v)
    await db.commit()
    return {"status": "updated"}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(proj)
    await db.commit()
    return {"status": "deleted"}


@router.post("/projects/{project_id}/extend")
async def extend_project(project_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    days: int = int(payload.get("days", 30))
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    from datetime import timedelta, datetime as dt
    base = proj.expires_at or dt.utcnow()
    proj.expires_at = base + timedelta(days=days)
    await db.commit()
    return {"expires_at": proj.expires_at.isoformat()}
    proj = await db.get(Project, project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": proj.id,
        "company_id": proj.company_id,
        "name": proj.name,
        "slug": proj.slug,
        "folder_path": proj.folder_path,
        "description": proj.description,
        "project_type": proj.project_type,
        "subscription_type": proj.subscription_type,
        "starts_at": _iso(proj.starts_at),
        "expires_at": _iso(proj.expires_at),
        "auto_renew": bool(proj.auto_renew),
        "status": proj.status,
        "notify_before_expiry_days": proj.notify_before_expiry_days,
        "tags": proj.tags,
    }


def _parse_dt(v: Optional[str]):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _iso(v: Optional[datetime]):
    return v.isoformat() if v else None


def _parse_tags(v: Optional[str]) -> Optional[List[str]]:
    if not v:
        return None
    return [t.strip() for t in v.split(",") if t.strip()]
