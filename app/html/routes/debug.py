from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from app.api.routes.auth import get_current_user_optional
from app.html.deps import get_html_db

router = APIRouter()

@router.get("/debug-auth")
async def debug_auth(
    request: Request,
    current_user=Depends(get_current_user_optional)
):
    """Debug authentication endpoint"""
    return JSONResponse({
        "authenticated": current_user is not None,
        "user_id": current_user.id if current_user else None,
        "email": current_user.email if current_user else None,
        "is_active": current_user.is_active if current_user else None,
        "cookies": dict(request.cookies),
        "headers": dict(request.headers)
    })