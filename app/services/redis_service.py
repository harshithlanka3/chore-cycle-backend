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
    
    def get_all_chores(self) -> List[Chore]:
        chore_keys = self.redis_client.keys("chore:*")
        chores = []
        for key in chore_keys:
            chore_data = self.redis_client.get(key)
            if chore_data:
                chores.append(Chore.parse_raw(chore_data))
        return chores
    
    def get_chore(self, chore_id: str) -> Optional[Chore]:
        chore_data = self.redis_client.get(f"chore:{chore_id}")
        if chore_data:
            return Chore.parse_raw(chore_data)
        return None
    
    def save_chore(self, chore: Chore) -> None:
        self.redis_client.set(f"chore:{chore.id}", chore.json())
    
    def delete_chore(self, chore_id: str) -> bool:
        return bool(self.redis_client.delete(f"chore:{chore_id}"))
    
    def publish_update(self, update: dict) -> None:
        self.redis_client.publish("chore_updates", json.dumps(update))

redis_service = RedisService()