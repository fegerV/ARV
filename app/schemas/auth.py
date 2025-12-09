from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str
    user: 'UserResponse'

class TokenData(BaseModel):
    """Data encoded in JWT token"""
    user_id: int
    email: str
    role: str
    exp: datetime

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginError(BaseModel):
    detail: str
    locked_until: Optional[datetime] = None
    attempts_left: Optional[int] = None