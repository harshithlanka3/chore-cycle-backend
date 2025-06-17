from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import uuid4
from app.models.chore import Chore, Person, CreateChoreRequest, AddPersonRequest, JoinChoreRequest
from app.models.user import User
from app.services.redis_service import redis_service
from app.services.auth_service import current_active_user

router = APIRouter(prefix="/chores", tags=["chores"])

@router.get("/", response_model=List[Chore])
async def get_all_chores(current_user: User = Depends(current_active_user)):
    """Get all chores for the current user"""
    return redis_service.get_all_chores(current_user.id)

@router.get("/{chore_id}", response_model=Chore)
async def get_chore(chore_id: str, current_user: User = Depends(current_active_user)):
    """Get a specific chore by ID"""
    chore = redis_service.get_chore(chore_id, current_user.id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found or access denied")
    return chore

@router.post("/", response_model=Chore)
async def create_chore(request: CreateChoreRequest, current_user: User = Depends(current_active_user)):
    """Create a new chore"""
    chore = Chore(
        id=str(uuid4()),
        name=request.name,
        owner_id=current_user.id,
        shared_with=[],
        people=[],
        current_person_index=0
    )
    
    # Add creator as first person in the queue
    creator_person = Person(id=current_user.id, name=current_user.name, user_id=current_user.id)
    chore.people.append(creator_person)
    
    redis_service.save_chore(chore)
    
    # Broadcast update - only to owner initially since no one else has access yet
    redis_service.publish_update({
        "type": "chore_created",
        "chore_id": chore.id,
        "chore": chore.model_dump(),
        "user_id": current_user.id
    })
    
    return chore

@router.post("/join", response_model=Chore)
async def join_chore(request: JoinChoreRequest, current_user: User = Depends(current_active_user)):
    """Join a chore by ID"""
    chore = redis_service.join_chore(request.chore_id, current_user.id, current_user.name)
    if not chore:
        raise HTTPException(
            status_code=400, 
            detail="Chore not found, already joined, or you are the owner"
        )
    
    # Broadcast update to all participants (owner + all members)
    redis_service.publish_update({
        "type": "user_joined",
        "chore_id": request.chore_id,
        "chore": chore.model_dump(),
        "user_id": current_user.id,
        "user_name": current_user.name
    })
    
    return chore

@router.delete("/{chore_id}")
async def delete_chore(chore_id: str, current_user: User = Depends(current_active_user)):
    """Delete a chore - ONLY OWNER CAN DELETE"""
    # Get chore first to check ownership and get participant list for broadcasting
    chore = redis_service.get_chore_by_id(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    if chore.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the chore owner can delete this chore"
        )
    
    # Delete the chore
    if not redis_service.delete_chore(chore_id, current_user.id):
        raise HTTPException(
            status_code=500,
            detail="Failed to delete chore"
        )
    
    # Broadcast update to all participants before deletion
    redis_service.publish_update({
        "type": "chore_deleted",
        "chore_id": chore_id,
        "user_id": current_user.id
    })
    
    return {"message": "Chore deleted successfully"}

@router.post("/{chore_id}/people", response_model=Chore)
async def add_person_to_chore(chore_id: str, request: AddPersonRequest, current_user: User = Depends(current_active_user)):
    """Add a person to a chore (non-user person) - Owner and members can add people"""
    chore = redis_service.get_chore(chore_id, current_user.id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found or access denied")
    
    # Check if person name already exists
    if any(person.name.lower() == request.name.lower() for person in chore.people):
        raise HTTPException(status_code=400, detail="Person with this name already exists")
    
    new_person = Person(id=str(uuid4()), name=request.name, user_id=None)
    chore.people.append(new_person)
    redis_service.save_chore(chore)
    
    # Broadcast update to all participants
    redis_service.publish_update({
        "type": "person_added",
        "chore_id": chore_id,
        "chore": chore.model_dump(),
        "person": new_person.model_dump(),
        "user_id": current_user.id
    })
    
    return chore

@router.delete("/{chore_id}/people/{person_id}", response_model=Chore)
async def remove_person_from_chore(chore_id: str, person_id: str, current_user: User = Depends(current_active_user)):
    """Remove a person from a chore - ONLY OWNER CAN REMOVE PEOPLE"""
    chore = redis_service.get_chore(chore_id, current_user.id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found or access denied")
    
    # Only owner can remove people
    if chore.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="Only the chore owner can remove people from the chore"
        )
    
    # Find the person to remove
    person_index = None
    removed_person = None
    for i, person in enumerate(chore.people):
        if person.id == person_id:
            # Don't allow owner to remove themselves
            if person.user_id == current_user.id:
                raise HTTPException(
                    status_code=400, 
                    detail="Owner cannot remove themselves from the chore"
                )
            person_index = i
            removed_person = person
            break
    
    if person_index is None:
        raise HTTPException(status_code=404, detail="Person not found")
    
    # If removing a user (not just a person), also remove from shared_with
    if removed_person.user_id and removed_person.user_id in chore.shared_with:
        chore.shared_with.remove(removed_person.user_id)
    
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
    
    # Broadcast update - use different type based on whether it was a user or person
    update_type = "user_removed" if removed_person.user_id else "person_removed"
    redis_service.publish_update({
        "type": update_type,
        "chore_id": chore_id,
        "chore": chore.model_dump(),
        "removed_person": removed_person.model_dump(),
        "user_id": current_user.id
    })
    
    return chore

@router.post("/{chore_id}/leave")
async def leave_chore(chore_id: str, current_user: User = Depends(current_active_user)):
    """Leave a chore (remove yourself) - NON-OWNERS ONLY"""
    chore = redis_service.get_chore(chore_id, current_user.id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found or access denied")
    
    # Owner cannot leave their own chore
    if chore.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Owner cannot leave chore. Delete the chore instead.")
    
    # Remove user from shared_with list
    if current_user.id in chore.shared_with:
        chore.shared_with.remove(current_user.id)
    
    # Remove user from people list
    person_index = None
    for i, person in enumerate(chore.people):
        if person.user_id == current_user.id:
            person_index = i
            break
    
    if person_index is not None:
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
    
    # Broadcast update to remaining participants
    redis_service.publish_update({
        "type": "user_left",
        "chore_id": chore_id,
        "chore": chore.model_dump(),
        "user_id": current_user.id
    })
    
    return {"message": "Left chore successfully"}

@router.post("/{chore_id}/advance", response_model=Chore)
async def advance_queue(chore_id: str, current_user: User = Depends(current_active_user)):
    """Advance to the next person in the queue - Owner and members can advance"""
    chore = redis_service.get_chore(chore_id, current_user.id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found or access denied")
    
    if len(chore.people) == 0:
        raise HTTPException(status_code=400, detail="No people in chore")
    
    # Advance to next person
    chore.current_person_index = (chore.current_person_index + 1) % len(chore.people)
    redis_service.save_chore(chore)
    
    # Broadcast update to all participants
    redis_service.publish_update({
        "type": "queue_advanced",
        "chore_id": chore_id,
        "chore": chore.model_dump(),
        "new_current_person": chore.people[chore.current_person_index].model_dump(),
        "user_id": current_user.id
    })
    
    return chore