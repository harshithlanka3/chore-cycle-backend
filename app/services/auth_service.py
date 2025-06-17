import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_access_token(self, user_id: str) -> str:
        """Create a JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode = {"sub": user_id, "exp": expire}
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[str]:
        """Verify JWT token and return user ID"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except jwt.PyJWTError:
            return None
    
    def get_redis_client(self):
        """Get Redis client from redis_service"""
        from app.services.redis_service import redis_service
        return redis_service.redis_client
    
    def get_user_by_email(self, email: str):
        """Get user by email"""
        from app.models.user import User
        redis_client = self.get_redis_client()
        user_data = redis_client.get(f"user_email:{email.lower()}")
        if user_data:
            return User.parse_raw(user_data)
        return None
    
    def get_user_by_id(self, user_id: str):
        """Get user by ID"""
        from app.models.user import User
        redis_client = self.get_redis_client()
        user_data = redis_client.get(f"user:{user_id}")
        if user_data:
            return User.parse_raw(user_data)
        return None
    
    def create_user(self, email: str, full_name: str, password: str):
        """Create a new user"""
        from app.models.user import User
        
        user_id = str(uuid4())
        hashed_password = self.hash_password(password)
        
        user = User(
            id=user_id,
            email=email.lower(),
            full_name=full_name,
            hashed_password=hashed_password,
            created_at=datetime.utcnow(),
            chore_ids=[]
        )
        
        # Save user with multiple keys for lookup
        redis_client = self.get_redis_client()
        redis_client.set(f"user:{user_id}", user.json())
        redis_client.set(f"user_email:{email.lower()}", user.json())
        
        return user
    
    def update_user(self, user) -> None:
        """Update user in Redis"""
        redis_client = self.get_redis_client()
        redis_client.set(f"user:{user.id}", user.json())
        redis_client.set(f"user_email:{user.email.lower()}", user.json())
    
    def user_to_response(self, user):
        """Convert User to UserResponse (excluding sensitive data)"""
        from app.models.user import UserResponse
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            chore_ids=user.chore_ids
        )

# Create the auth_service instance
auth_service = AuthService()