from pydantic import BaseModel
from typing import List, Optional

class Person(BaseModel):
    id: str
    name: str  # This will now be the full_name
    user_id: str  # Reference to the actual user

class Chore(BaseModel):
    id: str
    name: str
    people: List[Person] = []
    current_person_index: int = 0
    created_by: str  # User ID of the creator
    created_by_name: str  # Full name of the creator

class CreateChoreRequest(BaseModel):
    name: str

class AddPersonRequest(BaseModel):
    email: str  # Changed from username to email

class ChoreUpdate(BaseModel):
    chore_id: str
    action: str
    data: Optional[dict] = None