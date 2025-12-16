from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

# ============ Storage Connections ============

class StorageConnectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: Literal["local_disk"] = "local_disk"  # Simplified to only local_disk
    metadata: Optional[Dict[str, Any]] = {}

class StorageConnectionCreate(StorageConnectionBase):
    base_path: str = Field(..., description="Base path for local storage")
    is_default: Optional[bool] = False

class StorageConnectionUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    base_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class StorageConnection(StorageConnectionBase):
    id: int
    is_active: bool
    base_path: str
    is_default: Optional[bool] = False
    last_tested_at: Optional[datetime]
    test_status: Optional[str]
    test_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============ Storage Folders ============

class StorageFolderCreate(BaseModel):
    company_id: int
    name: str
    folder_type: Literal["ar_content", "videos", "markers", "thumbnails", "qr-codes"]

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

# ============ Storage Usage Stats ============

class StorageUsageStats(BaseModel):
    total_files: int
    total_size_bytes: int
    total_size_mb: float
    base_path: str


# ============ Storage Health Status ============

class StorageHealthStatus(BaseModel):
    status: str
    base_path: str
    total_disk_space_gb: float
    used_disk_space_gb: float
    free_disk_space_gb: float
    disk_usage_percent: float
    storage_files_count: int
    storage_size_mb: float
    is_writable: bool