from fastapi_users import schemas
from pydantic import BaseModel
from typing import Optional

class UserRead(schemas.BaseUser[str]):
    id: str
    email: str
    name: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False

class UserCreate(schemas.BaseUserCreate):
    email: str
    password: str
    name: str
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False

class UserUpdate(schemas.BaseUserUpdate):
    password: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None

class User(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    hashed_password: str

    class Config:
        from_attributes = True