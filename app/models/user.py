from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    MEMBER = "member"
    ADMIN = "admin"

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    chore_ids: List[str] = []  # List of chore IDs the user is part of

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime
    chore_ids: List[str] = []

class UserRegistrationRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class JoinChoreRequest(BaseModel):
    chore_id: str