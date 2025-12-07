from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    # Contacts
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Storage (REQUIRED for new client companies)
    storage_connection_id: int = Field(
        ..., description=(
            "ID подключения к хранилищу (MinIO или Yandex Disk). "
            "Локальное хранилище Vertex AR недоступно для клиентов."
        ),
    )
    storage_path: Optional[str] = Field(
        None,
        description=(
            "Папка в Yandex Disk (например /Companies/MyCompany) "
            "или bucket name для MinIO. Auto-generated если не указан."
        ),
    )

    # Subscription
    subscription_tier: str = Field(default="basic")
    subscription_expires_at: Optional[datetime] = None

    # Quotas
    storage_quota_gb: int = Field(default=10, ge=1, le=1000)
    projects_limit: int = Field(default=50, ge=1, le=500)

    # Notes
    notes: Optional[str] = None


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    storage_connection_id: Optional[int] = None
    storage_path: Optional[str] = None
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    storage_quota_gb: Optional[int] = None
    projects_limit: Optional[int] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    slug: str

    contact_email: Optional[str]
    contact_phone: Optional[str]
    telegram_chat_id: Optional[str]

    storage_connection_id: int
    storage_path: str
    is_default: bool

    subscription_tier: Optional[str]
    subscription_expires_at: Optional[datetime]

    storage_quota_gb: Optional[int]
    storage_used_bytes: int
    projects_limit: Optional[int]

    is_active: bool
    notes: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True