from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import httpx
import logging
from urllib.parse import quote_plus

from app.core.database import get_db
from app.core.config import get_settings
from app.models.storage import StorageConnection
from app.utils.oauth_state import oauth_state_store
from app.utils.token_encryption import token_encryption

router = APIRouter(tags=["oauth"])
settings = get_settings()
logger = logging.getLogger(__name__)

@router.get("/authorize")
async def initiate_yandex_oauth(
    connection_name: str = Query(..., description="Название подключения"),
):
    """
    Шаг 1: Инициация OAuth авторизации с Яндекс Диском (popup)
    """
    # Validate redirect URI
    if not settings.YANDEX_OAUTH_REDIRECT_URI:
        raise HTTPException(
            status_code=500, 
            detail="YANDEX_OAUTH_REDIRECT_URI not configured"
        )
    
    # Create OAuth state using the state store
    state = await oauth_state_store.create_state(connection_name)
    
    # Build authorization URL
    auth_url = (
        f"https://oauth.yandex.ru/authorize?"
        f"response_type=code&"
        f"client_id={settings.YANDEX_OAUTH_CLIENT_ID}&"
        f"redirect_uri={settings.YANDEX_OAUTH_REDIRECT_URI}&"
        f"state={state}&"
        f"force_confirm=yes"
    )
    
    logger.info(
        "Yandex OAuth initiated",
        extra={
            "connection_name": connection_name,
            "state": state[:8] + "...",  # Log partial state for debugging
            "redirect_uri": settings.YANDEX_OAUTH_REDIRECT_URI
        }
    )
    
    return RedirectResponse(url=auth_url)

@router.get("/callback")
async def yandex_oauth_callback(
    background_tasks: BackgroundTasks,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Шаг 2: Callback после авторизации пользователя
    """
    # Verify and consume the state
    state_data = await oauth_state_store.get_and_delete_state(state)
    if not state_data:
        logger.warning("Invalid or expired OAuth state", extra={"state": state[:8] + "..."})
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired state parameter. Please try again."
        )
    
    connection_name = state_data["connection_name"]
    
    try:
        # Exchange authorization code for OAuth token
        async with httpx.AsyncClient(timeout=30.0) as client:
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
                logger.error(
                    "Failed to exchange code for token",
                    extra={
                        "status_code": response.status_code,
                        "response_text": response.text[:200],
                        "connection_name": connection_name
                    }
                )
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange authorization code. Please try again."
                )
            
            token_data = response.json()
            access_token = token_data.get("access_token")
            
            if not access_token:
                raise HTTPException(
                    status_code=500,
                    detail="No access token received from OAuth provider"
                )

        # Get disk information with the access token
        async with httpx.AsyncClient(timeout=30.0) as client:
            disk_info_response = await client.get(
                "https://cloud-api.yandex.net/v1/disk/",
                headers={"Authorization": f"OAuth {access_token}"},
            )
            
            if disk_info_response.status_code != 200:
                logger.error(
                    "Failed to get disk info",
                    extra={
                        "status_code": disk_info_response.status_code,
                        "response_text": disk_info_response.text[:200],
                        "connection_name": connection_name
                    }
                )
                raise HTTPException(
                    status_code=400,
                    detail="Failed to access Yandex Disk. Please check permissions."
                )
            
            disk_info = disk_info_response.json()

        # Prepare and encrypt credentials
        credentials = {
            "oauth_token": access_token,
            "refresh_token": token_data.get("refresh_token"),
            "expires_in": token_data.get("expires_in"),
            "token_type": token_data.get("token_type"),
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Encrypt credentials before storage
        encrypted_credentials = token_encryption.encrypt_credentials(credentials)

        # Create storage connection in database
        connection = StorageConnection(
            name=connection_name,
            provider="yandex_disk",
            credentials=encrypted_credentials,
            is_active=True,
            test_status="success",
            last_tested_at=datetime.utcnow(),
            metadata={
                "user_display_name": (disk_info.get("user") or {}).get("display_name"),
                "total_space": disk_info.get("total_space"),
                "used_space": disk_info.get("used_space"),
                "has_encryption": token_encryption.is_encryption_available(),
            },
        )
        
        db.add(connection)
        await db.commit()
        await db.refresh(connection)

        logger.info(
            "Yandex OAuth connection created successfully",
            extra={
                "connection_id": connection.id,
                "connection_name": connection_name,
                "has_encryption": token_encryption.is_encryption_available()
            }
        )

        # Schedule cleanup of expired states
        background_tasks.add_task(oauth_state_store.cleanup_expired_states)

        # Redirect to frontend OAuth callback page with success parameters
        redirect_url = f"{settings.ADMIN_FRONTEND_URL}/oauth/yandex/callback?success=true&connectionId={connection.id}"
        return RedirectResponse(url=redirect_url)
        
    except httpx.RequestError as e:
        logger.error(
            "Network error during OAuth callback",
            extra={"error": str(e), "connection_name": connection_name}
        )
        error_message = "Network error during authentication. Please try again."
        redirect_url = f"{settings.ADMIN_FRONTEND_URL}/oauth/yandex/callback?success=false&error={quote_plus(error_message)}"
        return RedirectResponse(url=redirect_url)
    except HTTPException as e:
        # Re-raise HTTP exceptions for proper status codes
        raise e
    except Exception as e:
        logger.error(
            "Unexpected error during OAuth callback",
            extra={"error": str(e), "connection_name": connection_name}
        )
        error_message = "An unexpected error occurred during authentication."
        redirect_url = f"{settings.ADMIN_FRONTEND_URL}/oauth/yandex/callback?success=false&error={quote_plus(error_message)}"
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
    # Get connection
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Storage connection not found")
    if conn.provider != "yandex_disk":
        raise HTTPException(status_code=400, detail="This endpoint only works for Yandex Disk")

    # Decrypt credentials to get OAuth token
    try:
        if isinstance(conn.credentials, str):
            credentials = token_encryption.decrypt_credentials(conn.credentials)
        else:
            credentials = conn.credentials or {}
        
        token = credentials.get("oauth_token")
        if not token:
            logger.error("Missing OAuth token in credentials", extra={"connection_id": connection_id})
            raise HTTPException(
                status_code=401, 
                detail="OAuth token not found. Please re-authenticate."
            )
    except Exception as e:
        logger.error("Failed to decrypt credentials", extra={"connection_id": connection_id, "error": str(e)})
        raise HTTPException(
            status_code=500,
            detail="Failed to access stored credentials. Please re-authenticate."
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://cloud-api.yandex.net/v1/disk/resources",
                params={"path": path, "limit": 100},
                headers={"Authorization": f"OAuth {token}"},
            )
            
            # Handle specific Yandex API errors
            if resp.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="OAuth token expired or invalid. Please re-authenticate."
                )
            elif resp.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied to this folder. Please check permissions."
                )
            elif resp.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail="Folder not found in Yandex Disk."
                )
            elif resp.status_code != 200:
                logger.error(
                    "Yandex API error",
                    extra={
                        "status_code": resp.status_code,
                        "response_text": resp.text[:200],
                        "path": path,
                        "connection_id": connection_id
                    }
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to access Yandex Disk. Please try again."
                )
            
            data = resp.json()
            items = (data.get("_embedded") or {}).get("items", [])
            
            # Filter only directories and include timestamps
            folders = [
                {
                    "name": i.get("name"),
                    "path": i.get("path"),
                    "type": i.get("type"),
                    "created": i.get("created"),
                    "modified": i.get("modified"),
                    "last_modified": i.get("modified"),  # Alias for frontend compatibility
                }
                for i in items
                if i.get("type") == "dir"
            ]
            
            # Calculate parent path for navigation
            if path == "/" or path == "":
                parent_path = "/"
                has_parent = False
            else:
                path_parts = path.rstrip("/").split("/")
                if len(path_parts) > 1:
                    parent_path = "/".join(path_parts[:-1]) or "/"
                    has_parent = True
                else:
                    parent_path = "/"
                    has_parent = False
            
            return {
                "current_path": path,
                "folders": folders,
                "parent_path": parent_path,
                "has_parent": has_parent,
            }
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request to Yandex Disk timed out. Please try again."
        )
    except httpx.RequestError as e:
        logger.error(
            "Network error accessing Yandex Disk",
            extra={"error": str(e), "connection_id": connection_id}
        )
        raise HTTPException(
            status_code=503,
            detail="Network error accessing Yandex Disk. Please try again."
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "Unexpected error listing folders",
            extra={"error": str(e), "connection_id": connection_id}
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while listing folders."
        )

@router.post("/{connection_id}/create-folder")
async def create_yandex_folder(
    connection_id: int,
    folder_path: str = Query(..., description="Путь новой папки"),
    db: AsyncSession = Depends(get_db),
):
    """
    Создание новой папки в Яндекс Диске
    """
    # Get connection
    conn = await db.get(StorageConnection, connection_id)
    if not conn:
        raise HTTPException(status_code=404, detail="Storage connection not found")
    if conn.provider != "yandex_disk":
        raise HTTPException(status_code=400, detail="This endpoint only works for Yandex Disk")

    # Decrypt credentials to get OAuth token
    try:
        if isinstance(conn.credentials, str):
            credentials = token_encryption.decrypt_credentials(conn.credentials)
        else:
            credentials = conn.credentials or {}
        
        token = credentials.get("oauth_token")
        if not token:
            logger.error("Missing OAuth token in credentials", extra={"connection_id": connection_id})
            raise HTTPException(
                status_code=401, 
                detail="OAuth token not found. Please re-authenticate."
            )
    except Exception as e:
        logger.error("Failed to decrypt credentials", extra={"connection_id": connection_id, "error": str(e)})
        raise HTTPException(
            status_code=500,
            detail="Failed to access stored credentials. Please re-authenticate."
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(
                "https://cloud-api.yandex.net/v1/disk/resources",
                params={"path": folder_path},
                headers={"Authorization": f"OAuth {token}"},
            )
            
            # Handle specific Yandex API errors
            if resp.status_code == 401:
                raise HTTPException(
                    status_code=401,
                    detail="OAuth token expired or invalid. Please re-authenticate."
                )
            elif resp.status_code == 403:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied. Cannot create folder in this location."
                )
            elif resp.status_code == 409:
                raise HTTPException(
                    status_code=409,
                    detail="Folder already exists at this location."
                )
            elif resp.status_code not in (201, 202):
                logger.error(
                    "Yandex API error creating folder",
                    extra={
                        "status_code": resp.status_code,
                        "response_text": resp.text[:200],
                        "folder_path": folder_path,
                        "connection_id": connection_id
                    }
                )
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create folder. Please try again."
                )
            
            logger.info(
                "Folder created successfully",
                extra={
                    "folder_path": folder_path,
                    "connection_id": connection_id
                }
            )
            
            return {
                "status": "success", 
                "message": f"Folder created: {folder_path}", 
                "path": folder_path
            }
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Request to Yandex Disk timed out. Please try again."
        )
    except httpx.RequestError as e:
        logger.error(
            "Network error creating folder",
            extra={"error": str(e), "connection_id": connection_id}
        )
        raise HTTPException(
            status_code=503,
            detail="Network error accessing Yandex Disk. Please try again."
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "Unexpected error creating folder",
            extra={"error": str(e), "connection_id": connection_id}
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while creating the folder."
        )
