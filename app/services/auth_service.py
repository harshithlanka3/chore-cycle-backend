import os
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import BaseUserDatabase

from app.models.user import User, UserCreate, UserUpdate
from app.services.user_database import RedisUserDatabase
from app.services.redis_service import redis_service

SECRET = os.getenv("SECRET_KEY", "your-super-secret-key")

class UserManager(BaseUserManager[User, str]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_login(self, user: User, request: Optional[Request] = None, response = None):
        print(f"User {user.id} has logged in.")

    async def on_after_forgot_password(self, user: User, token: str, request: Optional[Request] = None):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(self, user: User, token: str, request: Optional[Request] = None):
        print(f"Verification requested for user {user.id}. Verification token: {token}")

    def parse_id(self, value: str) -> str:
        """Parse the user ID from a string."""
        return value

async def get_user_db():
    yield RedisUserDatabase(redis_service.redis_client)

async def get_user_manager(user_db: BaseUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

# JWT Strategy
def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=SECRET,
        lifetime_seconds=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)) * 60,
    )

# Bearer transport
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

# Authentication backend
auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, str](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)