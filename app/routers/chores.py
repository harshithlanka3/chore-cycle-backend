from fastapi import APIRouter, HTTPException
from typing import List
from uuid import uuid4
from app.models.chore import Chore, Person, CreateChoreRequest, AddPersonRequest, ChoreUpdate
from app.services.redis_service import redis_service

router = APIRouter(prefix="/chores", tags=["chores"])

@router.get("/", response_model=List[Chore])
async def get_all_chores():
    """Get all chores"""
    return redis_service.get_all_chores()

@router.get("/{chore_id}", response_model=Chore)
async def get_chore(chore_id: str):
    """Get a specific chore by ID"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    return chore

@router.post("/", response_model=Chore)
async def create_chore(request: CreateChoreRequest):
    """Create a new chore"""
    chore = Chore(
        id=str(uuid4()),
        name=request.name,
        people=[],
        current_person_index=0
    )
    redis_service.save_chore(chore)
    
    # Broadcast update
    redis_service.publish_update({
        "type": "chore_created",
        "chore": chore.dict()
    })
    
    return chore

@router.delete("/{chore_id}")
async def delete_chore(chore_id: str):
    """Delete a chore"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    redis_service.delete_chore(chore_id)
    
    # Broadcast update
    redis_service.publish_update({
        "type": "chore_deleted",
        "chore_id": chore_id
    })
    
    return {"message": "Chore deleted successfully"}

@router.post("/{chore_id}/people", response_model=Chore)
async def add_person_to_chore(chore_id: str, request: AddPersonRequest):
    """Add a person to a chore"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if person name already exists
    if any(person.name.lower() == request.name.lower() for person in chore.people):
        raise HTTPException(status_code=400, detail="Person with this name already exists")
    
    new_person = Person(id=str(uuid4()), name=request.name)
    chore.people.append(new_person)
    redis_service.save_chore(chore)
    
    # Broadcast update
    redis_service.publish_update({
        "type": "person_added",
        "chore_id": chore_id,
        "chore": chore.dict(),
        "person": new_person.dict()
    })
    
    return chore

@router.delete("/{chore_id}/people/{person_id}", response_model=Chore)
async def remove_person_from_chore(chore_id: str, person_id: str):
    """Remove a person from a chore"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Find and remove the person
    person_index = None
    removed_person = None
    for i, person in enumerate(chore.people):
        if person.id == person_id:
            person_index = i
            removed_person = person
            break
    
    if person_index is None:
        raise HTTPException(status_code=404, detail="Person not found")
    
    chore.people.pop(person_index)
    
    # Adjust current_person_index if necessary
    if len(chore.people) == 0:
        chore.current_person_index = 0
    elif person_index <= chore.current_person_index:
        if chore.current_person_index > 0:
            chore.current_person_index -= 1
        elif chore.current_person_index >= len(chore.people):
            chore.current_person_index = 0
    
    redis_service.save_chore(chore)
    
    # Broadcast update
    redis_service.publish_update({
        "type": "person_removed",
        "chore_id": chore_id,
        "chore": chore.dict(),
        "removed_person": removed_person.dict()
    })
    
    return chore

@router.post("/{chore_id}/advance", response_model=Chore)
async def advance_queue(chore_id: str):
    """Advance to the next person in the queue"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    if len(chore.people) == 0:
        raise HTTPException(status_code=400, detail="No people in chore")
    
    # Advance to next person
    chore.current_person_index = (chore.current_person_index + 1) % len(chore.people)
    redis_service.save_chore(chore)
    
    # Broadcast update
    redis_service.publish_update({
        "type": "queue_advanced",
        "chore_id": chore_id,
        "chore": chore.dict(),
        "new_current_person": chore.people[chore.current_person_index].dict()
    })
    
    return chore