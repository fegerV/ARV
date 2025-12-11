from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.portrait import Portrait
from app.tasks.marker_tasks import generate_mind_marker_task
import aiofiles

router = APIRouter(prefix="/portraits", tags=["Portraits"])


def build_image_url(storage_base: str, saved_path: Path) -> str:
    """Map local saved path under STORAGE_BASE_PATH to public /storage URL."""
    base = Path(storage_base)
    rel = saved_path.relative_to(base)
    return f"/storage/{rel.as_posix()}"


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_portrait(
    file: UploadFile = File(...),
    company_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    # Ensure storage dir
    uid = uuid4()
    portrait_dir = Path(settings.STORAGE_BASE_PATH) / "portraits" / str(uid)
    portrait_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    image_path = portrait_dir / file.filename
    async with aiofiles.open(image_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await out.write(chunk)

    # Build public URL (served by nginx alias /storage)
    image_url = build_image_url(settings.STORAGE_BASE_PATH, image_path)

    # Create portrait record
    portrait = Portrait(
        unique_id=uid,
        image_path=str(image_path),
        image_url=image_url,
        marker_status="pending",
        portrait_metadata={},
    )

    db.add(portrait)
    await db.flush()
    await db.commit()
    await db.refresh(portrait)

    # Enqueue marker generation
    async_result = generate_mind_marker_task.delay(portrait.id)

    return {
        "id": portrait.id,
        "unique_id": str(portrait.unique_id),
        "image_url": portrait.image_url,
        "marker_status": portrait.marker_status,
        "task_id": async_result.id,
    }


@router.get("/{portrait_id}")
async def get_portrait(portrait_id: int, db: AsyncSession = Depends(get_db)):
    portrait = await db.get(Portrait, portrait_id)
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")
    return {
        "id": portrait.id,
        "unique_id": str(portrait.unique_id),
        "image_url": portrait.image_url,
        "marker_status": portrait.marker_status,
        "marker_url": portrait.marker_url,
        "metadata": portrait.portrait_metadata,
    }


@router.get("/by-unique/{unique_id}")
async def get_portrait_by_unique(unique_id: str, db: AsyncSession = Depends(get_db)):
    # Simple lookup by unique_id; raw SQLAlchemy 2.0 select is omitted for brevity
    from sqlalchemy import select
    stmt = select(Portrait).where(Portrait.unique_id == unique_id)
    result = await db.execute(stmt)
    portrait = result.scalar_one_or_none()
    if not portrait:
        raise HTTPException(status_code=404, detail="Portrait not found")
    return {
        "id": portrait.id,
        "unique_id": str(portrait.unique_id),
        "image_url": portrait.image_url,
        "marker_status": portrait.marker_status,
        "marker_url": portrait.marker_url,
        "metadata": portrait.portrait_metadata,
    }


@router.get("/portraits/{portrait_id}/active-video")
async def get_active_video(portrait_id: int):
    # Placeholder until videos are implemented
    # Return 404 to indicate no active video assigned yet
    raise HTTPException(status_code=404, detail="Active video not implemented")


@router.get("/by-unique/{unique_id}/active-video")
async def get_active_video_by_unique(unique_id: str):
    # Placeholder
    raise HTTPException(status_code=404, detail="Active video not implemented")