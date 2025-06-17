import redis
import json
from typing import List, Optional
from app.models.chore import Chore, Person
import os
from dotenv import load_dotenv

load_dotenv()

class RedisService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
    
    def get_all_chores(self, user_id: str) -> List[Chore]:
        """Get all chores that user owns or has joined"""
        chore_keys = self.redis_client.keys("chore:*")
        chores = []
        for key in chore_keys:
            chore_data = self.redis_client.get(key)
            if chore_data:
                chore = Chore.model_validate_json(chore_data)
                # Check if user owns or has joined this chore
                if chore.owner_id == user_id or user_id in chore.shared_with:
                    chores.append(chore)
        return chores
    
    def get_chore(self, chore_id: str, user_id: str) -> Optional[Chore]:
        """Get a chore if user has access to it"""
        chore_data = self.redis_client.get(f"chore:{chore_id}")
        if chore_data:
            chore = Chore.model_validate_json(chore_data)
            # Check if user owns or has joined this chore
            if chore.owner_id == user_id or user_id in chore.shared_with:
                return chore
        return None
    
    def get_chore_by_id(self, chore_id: str) -> Optional[Chore]:
        """Get chore by ID without user access check (for joining)"""
        chore_data = self.redis_client.get(f"chore:{chore_id}")
        if chore_data:
            return Chore.model_validate_json(chore_data)
        return None
    
    def save_chore(self, chore: Chore) -> None:
        self.redis_client.set(f"chore:{chore.id}", chore.model_dump_json())
    
    def delete_chore(self, chore_id: str, user_id: str) -> bool:
        """Delete chore - ONLY OWNER CAN DELETE"""
        chore = self.get_chore_by_id(chore_id)
        if chore and chore.owner_id == user_id:  # Only owner can delete
            return bool(self.redis_client.delete(f"chore:{chore_id}"))
        return False
    
    def join_chore(self, chore_id: str, user_id: str, user_name: str) -> Optional[Chore]:
        """Join a chore by ID"""
        chore = self.get_chore_by_id(chore_id)
        if chore and user_id not in chore.shared_with and user_id != chore.owner_id:
            # Add user to shared_with list
            chore.shared_with.append(user_id)
            
            # Add user as a person in the queue
            new_person = Person(id=user_id, name=user_name, user_id=user_id)
            chore.people.append(new_person)
            
            self.save_chore(chore)
            return chore
        return None
    
    def publish_update(self, update: dict) -> None:
        self.redis_client.publish("chore_updates", json.dumps(update))

redis_service = RedisService()