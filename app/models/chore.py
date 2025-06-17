from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4

class Person(BaseModel):
    id: str
    name: str
    user_id: Optional[str] = None  # NEW: Track which user this person represents

class Chore(BaseModel):
    id: str
    name: str
    owner_id: str
    shared_with: List[str] = []  # Users who have joined this chore
    people: List[Person] = []
    current_person_index: int = 0

class CreateChoreRequest(BaseModel):
    name: str

class AddPersonRequest(BaseModel):
    name: str

class JoinChoreRequest(BaseModel):  # NEW: Replace ShareChoreRequest
    chore_id: str

class ChoreUpdate(BaseModel):
    chore_id: str
    action: str
    data: Optional[dict] = None