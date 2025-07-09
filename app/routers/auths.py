from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import (
    UserRegistrationRequest, 
    UserLoginRequest, 
    TokenResponse, 
    UserResponse,
    JoinChoreRequest
)
from app.dependencies.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=TokenResponse)
async def register(request: UserRegistrationRequest):
    """Register a new user"""
    from app.services.auth_service import auth_service
    
    # Check if email already exists
    if auth_service.get_user_by_email(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = auth_service.create_user(
        email=request.email,
        full_name=request.full_name,
        password=request.password
    )
    
    # Create access token
    access_token = auth_service.create_access_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=auth_service.user_to_response(user)
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: UserLoginRequest):
    """Login user"""
    from app.services.auth_service import auth_service
    
    user = auth_service.get_user_by_email(request.email)
    
    if not user or not auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = auth_service.create_access_token(user.id)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=auth_service.user_to_response(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    from app.services.auth_service import auth_service
    return auth_service.user_to_response(current_user)

@router.post("/join-chore", response_model=UserResponse)
async def join_chore(
    request: JoinChoreRequest,
    current_user: User = Depends(get_current_user)
):
    """Join a chore by ID"""
    from app.services.auth_service import auth_service
    from app.services.redis_service import redis_service
    
    # Check if chore exists
    chore = redis_service.get_chore(request.chore_id)
    if not chore:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chore not found"
        )
    
    # Check if user is already in the chore's people list
    if any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already part of this chore"
        )
    
    # Add user to chore's people list
    from app.models.chore import Person
    from uuid import uuid4
    
    new_person = Person(
        id=str(uuid4()), 
        name=current_user.full_name,
        user_id=current_user.id
    )
    chore.people.append(new_person)
    redis_service.save_chore(chore)
    
    # Add chore to user's chore list
    if request.chore_id not in current_user.chore_ids:
        current_user.chore_ids.append(request.chore_id)
        auth_service.update_user(current_user)
    
    # Get all participants for broadcast
    participant_ids = [person.user_id for person in chore.people]
    
    # Broadcast update to all participants
    redis_service.publish_update({
        "type": "person_added",
        "chore_id": request.chore_id,
        "chore": chore.dict(),
        "person": new_person.dict(),
        "participants": participant_ids
    })
    
    return auth_service.user_to_response(current_user)