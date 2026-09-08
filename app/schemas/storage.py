from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

# ============ Storage Connections ============

class StorageConnectionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: Literal["local_disk"] = "local_disk"  # Simplified to only local_disk
    metadata: dict[str, Any] | None = Field(default_factory=dict)

class StorageConnectionCreate(StorageConnectionBase):
    base_path: str = Field(..., description="Base path for local storage")
    is_default: bool | None = False

class StorageConnectionUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    base_path: str | None = None
    metadata: dict[str, Any] | None = None

class StorageConnection(StorageConnectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    base_path: str
    is_default: bool | None = False
    last_tested_at: datetime | None
    test_status: str | None
    test_error: str | None
    created_at: datetime
    updated_at: datetime

# ============ Company Storage Settings ============

class CompanyStorageSettings(BaseModel):
    storage_connection_id: int
    storage_path: str
    storage_quota_gb: int | None = None

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