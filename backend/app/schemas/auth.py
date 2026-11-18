from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters")

class UserLogin(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    account_status: str
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None
    type: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters")

class EmailVerificationRequest(BaseModel):
    token: str
