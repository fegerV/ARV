from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    last_login_at: datetime | None = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: int
    email: str
    role: str
    exp: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginError(BaseModel):
    detail: str
    locked_until: datetime | None = None
    attempts_left: int | None = None


class RegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name must be between 2 and 100 characters")
    role: str = "admin"  # Простая строка вместо ENUM
    company_id: int | None = Field(
        default=None,
        description="Company the new user belongs to. Required for non-super-admin users.",
    )
    is_super_admin: bool = Field(
        default=False,
        description="Whether the new user is a global super admin. Only a super admin can set this.",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {"admin", "editor", "user"}
        if v not in allowed:
            raise ValueError(f"role must be one of {sorted(allowed)}")
        return v
    

class RegisterResponse(BaseModel):
    """User registration response model"""
    user: UserResponse
    message: str = "User created successfully"