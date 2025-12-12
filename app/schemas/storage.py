from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal
from datetime import datetime

# ============ Storage Connections ============

class StorageConnectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: Literal["local_disk", "minio", "yandex_disk"]
    metadata: Optional[Dict[str, Any]] = {}

class MinIOCredentials(BaseModel):
    endpoint: str = Field(..., example="minio:9000")
    access_key: str
    secret_key: str
    secure: bool = False
    region: str = "us-east-1"

class YandexDiskCredentials(BaseModel):
    oauth_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None

class StorageConnectionCreate(StorageConnectionBase):
    base_path: Optional[str] = None
    is_default: Optional[bool] = False
    credentials: Optional[Dict[str, Any]] = None  # MinIOCredentials or YandexDiskCredentials

    @validator("credentials", always=True)
    def validate_credentials(cls, v, values):
        provider = values.get("provider")
        if provider == "minio":
            MinIOCredentials(**(v or {}))
        elif provider == "yandex_disk":
            YandexDiskCredentials(**(v or {}))
        elif provider == "local_disk":
            # credentials optional; ensure base_path provided either here or via base_path field
            creds = v or {}
            if not (creds.get("base_path") or values.get("base_path")):
                raise ValueError("base_path is required for local_disk provider")
        return v

class StorageConnectionUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class StorageConnection(StorageConnectionBase):
    id: int
    is_active: bool
    base_path: Optional[str] = None
    is_default: Optional[bool] = False
    last_tested_at: Optional[datetime]
    test_status: Optional[str]
    test_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============ Storage Folders ============

class YandexDiskFolder(BaseModel):
    name: str
    path: str
    type: str  # 'dir' or 'file'
    created: datetime
    modified: datetime
    size: Optional[int] = 0

class StorageFolderCreate(BaseModel):
    company_id: int
    name: str
    folder_type: Literal["ar_content", "videos", "markers", "custom"]

class StorageFolderResponse(BaseModel):
    id: int
    company_id: int
    name: str
    path: str
    folder_type: str
    files_count: int
    total_size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True

# ============ Company Storage Settings ============

class CompanyStorageSettings(BaseModel):
    storage_connection_id: int
    storage_path: str
    storage_quota_gb: Optional[int] = None

class CompanyCreate(BaseModel):
    name: str
    storage_settings: Optional[CompanyStorageSettings] = None