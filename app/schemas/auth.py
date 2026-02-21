from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


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
    locked_until: Optional[datetime] = None
    attempts_left: Optional[int] = None


class RegisterRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name must be between 2 and 100 characters")
    role: str = "admin"  # Простая строка вместо ENUM
    

class RegisterResponse(BaseModel):
    """User registration response model"""
    user: UserResponse
    message: str = "User created successfully"