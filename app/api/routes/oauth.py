from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import httpx
import secrets

from app.core.database import get_db
from app.core.config import get_settings
from app.models.storage import StorageConnection

router = APIRouter(prefix="/api/oauth/yandex", tags=["oauth"])
settings = get_settings()

# Временное хранилище state для защиты от CSRF (в production заменить на Redis)
oauth_states: dict[str, dict] = {}

@router.get("/authorize")
async def initiate_yandex_oauth(
    connection_name: str = Query(..., description="Название подключения"),
):
    """
    Шаг 1: Инициация OAuth авторизации с Яндекс Диском (popup)
    """
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "connection_name": connection_name,
        "timestamp": datetime.utcnow().timestamp(),
    }
    auth_url = (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&"
        f"client_id={settings.YANDEX_OAUTH_CLIENT_ID}&"
        f"redirect_uri={settings.YANDEX_OAUTH_REDIRECT_URI}&"
        f"state={state}&"
        f"force_confirm=yes"
    )
    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def yandex_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Шаг 2: Callback после авторизации пользователя
    """
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    connection_name = oauth_states[state]["connection_name"]
    del oauth_states[state]

    # Обмениваем code на OAuth token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth.yandex.ru/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.YANDEX_OAUTH_CLIENT_ID,
                "client_secret": settings.YANDEX_OAUTH_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Failed to get token: {response.text}")
        token_data = response.json()

    # Получаем информацию о диске
    async with httpx.AsyncClient() as client:
        disk_info_response = await client.get(
            "https://cloud-api.yandex.net/v1/disk/",
            headers={"Authorization": f"OAuth {token_data['access_token']}"},
        )
        if disk_info_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get disk info")
        disk_info = disk_info_response.json()

    # Создаем подключение в БД (без шифрования для простоты; можно заменить на KMS/secret vault)
    credentials = {
        "oauth_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "expires_in": token_data.get("expires_in"),
        "token_type": token_data.get("token_type"),
    }
    connection = StorageConnection(
        name=connection_name,
        provider="yandex_disk",
        credentials=credentials,
        is_active=True,
        test_status="success",
        last_tested_at=datetime.utcnow(),
        metadata={
            "user_display_name": (disk_info.get("user") or {}).get("display_name"),
            "total_space": disk_info.get("total_space"),
            "used_space": disk_info.get("used_space"),
        },
    )
    db.add(connection)
    await db.commit()
    await db.refresh(connection)

    redirect_url = f"{settings.ADMIN_FRONTEND_URL}/storage/connections/{connection.id}?success=true"
    return RedirectResponse(url=redirect_url)

@router.get("/{connection_id}/folders")
async def list_yandex_folders(
    connection_id: int,
    path: str = Query("/", description="Путь в Яндекс Диске"),
    db: AsyncSession = Depends(get_db),
):
    """
    Получение списка папок в Яндекс Диске (для file picker)
    """
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Storage connection not found")
    if conn.provider != "yandex_disk":
        raise HTTPException(status_code=400, detail="This endpoint only works for Yandex Disk")

    token = (conn.credentials or {}).get("oauth_token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing OAuth token in credentials")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://cloud-api.yandex.net/v1/disk/resources",
                params={"path": path, "limit": 100},
                headers={"Authorization": f"OAuth {token}"},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to list folders: {resp.text}")
            data = resp.json()
            items = (data.get("_embedded") or {}).get("items", [])
            folders = [
                {
                    "name": i.get("name"),
                    "path": i.get("path"),
                    "type": i.get("type"),
                    "created": i.get("created"),
                    "modified": i.get("modified"),
                }
                for i in items
                if i.get("type") == "dir"
            ]
            parent = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
            return {"current_path": path, "folders": folders, "parent_path": parent}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list folders: {str(e)}")

@router.post("/{connection_id}/create-folder")
async def create_yandex_folder(
    connection_id: int,
    folder_path: str = Query(..., description="Путь новой папки"),
    db: AsyncSession = Depends(get_db),
):
    """
    Создание новой папки в Яндекс Диске
    """
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Storage connection not found")
    if conn.provider != "yandex_disk":
        raise HTTPException(status_code=400, detail="This endpoint only works for Yandex Disk")
    token = (conn.credentials or {}).get("oauth_token")
    if not token:
        raise HTTPException(status_code=400, detail="Missing OAuth token in credentials")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                "https://cloud-api.yandex.net/v1/disk/resources",
                params={"path": folder_path},
                headers={"Authorization": f"OAuth {token}"},
            )
            if resp.status_code not in (201, 202):
                raise HTTPException(status_code=500, detail=f"Error creating folder: {resp.text}")
            return {"status": "success", "message": f"Folder created: {folder_path}", "path": folder_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating folder: {str(e)}")
