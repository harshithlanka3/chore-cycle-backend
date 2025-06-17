from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import auth_backend, fastapi_users, current_active_user
from app.models.user import User, UserRead, UserCreate, UserUpdate

router = APIRouter()

# Include FastAPI-Users auth routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend), 
    prefix="/jwt", 
    tags=["auth"]
)

router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="",
    tags=["auth"],
)

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

@router.get("/me", response_model=UserRead)
async def get_current_user(user: User = Depends(current_active_user)):
    """Get current authenticated user"""
    return user