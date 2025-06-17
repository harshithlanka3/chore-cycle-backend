import redis
import json
from typing import Optional, Dict, Any
from fastapi_users.db import BaseUserDatabase
from app.models.user import User, UserCreate, UserUpdate
import bcrypt
from uuid import uuid4

class RedisUserDatabase(BaseUserDatabase[User, str]):
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def get(self, id: str) -> Optional[User]:
        user_data = self.redis.get(f"user:{id}")
        if user_data:
            return User(**json.loads(user_data))
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        # Get user ID by email lookup
        user_id = self.redis.get(f"user_email:{email}")
        if user_id:
            return await self.get(user_id)  # Remove .decode() since user_id is already a string
        return None

    async def create(self, user_dict: Dict[str, Any]) -> User:
        # Generate ID if not provided
        if 'id' not in user_dict:
            user_dict['id'] = str(uuid4())
        
        # Set default values for required fields if not provided
        user_dict.setdefault('is_active', True)
        user_dict.setdefault('is_superuser', False)
        user_dict.setdefault('is_verified', False)
        
        # Hash password
        if 'password' in user_dict:
            hashed_password = bcrypt.hashpw(
                user_dict['password'].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            user_dict['hashed_password'] = hashed_password
            del user_dict['password']

        user = User(**user_dict)
        
        # Store user
        self.redis.set(f"user:{user.id}", user.model_dump_json())
        # Store email lookup
        self.redis.set(f"user_email:{user.email}", user.id)
        
        return user

    async def update(self, user: User, update_dict: Dict[str, Any]) -> User:
        # Handle password update
        if 'password' in update_dict and update_dict['password'] is not None:
            hashed_password = bcrypt.hashpw(
                update_dict['password'].encode('utf-8'), 
                bcrypt.gensalt()
            ).decode('utf-8')
            update_dict['hashed_password'] = hashed_password
            del update_dict['password']

        # Update user fields
        user_dict = user.model_dump()
        user_dict.update({k: v for k, v in update_dict.items() if v is not None})
        
        updated_user = User(**user_dict)
        
        # Store updated user
        self.redis.set(f"user:{updated_user.id}", updated_user.model_dump_json())
        
        return updated_user

    async def delete(self, user: User) -> None:
        self.redis.delete(f"user:{user.id}")
        self.redis.delete(f"user_email:{user.email}")

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))