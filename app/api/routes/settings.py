from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/settings")
async def get_settings():
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "public_url": settings.PUBLIC_URL,
    }
