from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.api.routes.auth import get_current_active_user

router = APIRouter()


@router.get("/settings")
async def get_settings_endpoint(current_user = Depends(get_current_active_user)):
    if not getattr(current_user, 'is_super_admin', False):
        raise HTTPException(status_code=403, detail="Admin access required")
    settings = get_settings()
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "public_url": settings.PUBLIC_URL,
    }
