"""AI Pipeline endpoints for AR content processing."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from app.api.routes.auth import get_current_active_user
from app.core.database import AsyncSession, get_db
from app.models.ar_content import ARContent
from app.models.user import User

router = APIRouter(tags=["AI Pipeline"])


class AIJobCreate(BaseModel):
    ar_content_id: int
    model_version: str = "default"


class AIJobStatus(BaseModel):
    job_id: str
    ar_content_id: int
    status: str
    progress: int
    result: Optional[dict] = None
    error: Optional[str] = None


_jobs: Dict[str, dict] = {}


async def _process_ai_job(job_id: str, ar_content_id: int) -> None:
    """Simulate AI processing with progress updates."""
    job = _jobs.setdefault(job_id, {
        "job_id": job_id,
        "ar_content_id": ar_content_id,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    })

    try:
        job["status"] = "processing"

        for i in range(1, 6):
            await asyncio.sleep(0.5)
            job["progress"] = i * 20

        job["status"] = "completed"
        job["progress"] = 100
        job["result"] = {
            "ar_content_id": ar_content_id,
            "processed_at": time.time(),
            "model_version": "default",
            "summary": "AI processing completed successfully",
        }
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)


@router.post("/process", response_model=AIJobStatus)
async def start_ai_processing(
    payload: AIJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Start AI processing for an AR content item."""
    ar_content = await db.get(ARContent, payload.ar_content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")

    job_id = str(uuid.uuid4())
    job: dict = {
        "job_id": job_id,
        "ar_content_id": payload.ar_content_id,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    _jobs[job_id] = job

    background_tasks.add_task(_process_ai_job, job_id, payload.ar_content_id)

    return AIJobStatus(**job)


@router.get("/jobs/{job_id}", response_model=AIJobStatus)
async def get_ai_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of an AI processing job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    ar_content_id = job.get("ar_content_id")
    if ar_content_id is not None and not getattr(current_user, 'is_super_admin', False):
        ar_content = await db.get(ARContent, ar_content_id)
        if not ar_content or (
            getattr(current_user, 'company_id', None) is not None and
            ar_content.company_id != getattr(current_user, 'company_id', None)
        ):
            raise HTTPException(status_code=403, detail="Access denied to this job")

    return AIJobStatus(**job)
