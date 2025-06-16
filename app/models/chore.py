from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4

class Person(BaseModel):
    id: str
    name: str

class Chore(BaseModel):
    id: str
    name: str
    people: List[Person] = []
    current_person_index: int = 0

class CreateChoreRequest(BaseModel):
    name: str

class AddPersonRequest(BaseModel):
    name: str

class ChoreUpdate(BaseModel):
    chore_id: str
    action: str  # "advance", "add_person", "remove_person", "delete_chore"
    data: Optional[dict] = None