from fastapi import APIRouter, HTTPException, Depends
from typing import List
from uuid import uuid4
from app.models.chore import Chore, Person, CreateChoreRequest, AddPersonRequest, ChoreUpdate
from app.models.user import User
from app.services.redis_service import redis_service
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/chores", tags=["chores"])

@router.get("/", response_model=List[Chore])
async def get_all_chores(current_user: User = Depends(get_current_user)):
    """Get all chores where the current user is a participant"""
    try:
        all_chores = redis_service.get_all_chores()
        user_chores = []
        
        for chore in all_chores:
            # Only include chores where the user is in the people list
            if any(person.user_id == current_user.id for person in chore.people):
                user_chores.append(chore)
        
        return user_chores
    except Exception as e:
        print(f"Error in get_all_chores: {e}")
        return []

@router.get("/{chore_id}", response_model=Chore)
async def get_chore(chore_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific chore by ID"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if user is in the chore's people list
    if not any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(status_code=403, detail="You don't have access to this chore")
    
    return chore

@router.post("/", response_model=Chore)
async def create_chore(
    request: CreateChoreRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new chore"""
    from app.services.auth_service import auth_service
    
    chore_id = str(uuid4())
    
    # Create chore with the creator as the first person
    creator_person = Person(
        id=str(uuid4()), 
        name=current_user.full_name,
        user_id=current_user.id
    )
    
    chore = Chore(
        id=chore_id,
        name=request.name,
        people=[creator_person],
        current_person_index=0,
        created_by=current_user.id,
        created_by_name=current_user.full_name
    )
    redis_service.save_chore(chore)
    
    # Add chore to user's chore list for reference
    current_user.chore_ids.append(chore_id)
    auth_service.update_user(current_user)
    
    # Broadcast update only to participants (handled by WebSocket)
    redis_service.publish_update({
        "type": "chore_created",
        "chore": chore.dict(),
        "participants": [current_user.id]  # Only creator initially
    })
    
    return chore

@router.delete("/{chore_id}")
async def delete_chore(chore_id: str, current_user: User = Depends(get_current_user)):
    """Delete a chore (only creator can delete)"""
    from app.services.auth_service import auth_service
    from app.models.user import User
    
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if user has access to this chore
    if not any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(status_code=403, detail="You don't have access to this chore")
    
    # Only the creator can delete the chore
    if chore.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the creator can delete this chore")
    
    # Get all participants before deletion for cleanup
    participant_ids = [person.user_id for person in chore.people]
    
    # Remove chore from all participants' chore lists
    redis_client = redis_service.redis_client
    for user_id in participant_ids:
        user_data = redis_client.get(f"user:{user_id}")
        if user_data:
            user = User.parse_raw(user_data)
            if chore_id in user.chore_ids:
                user.chore_ids.remove(chore_id)
                auth_service.update_user(user)
    
    redis_service.delete_chore(chore_id)
    
    # Broadcast update to all participants
    redis_service.publish_update({
        "type": "chore_deleted",
        "chore_id": chore_id,
        "participants": participant_ids
    })
    
    return {"message": "Chore deleted successfully"}

@router.post("/{chore_id}/people", response_model=Chore)
async def add_person_to_chore(
    chore_id: str, 
    request: AddPersonRequest,
    current_user: User = Depends(get_current_user)
):
    """Add a registered user to a chore by email"""
    from app.services.auth_service import auth_service
    
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if current user has access to this chore
    if not any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(status_code=403, detail="You don't have access to this chore")
    
    # Check if the email exists as a registered user
    target_user = auth_service.get_user_by_email(request.email)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if person is already in the chore
    if any(person.user_id == target_user.id for person in chore.people):
        raise HTTPException(status_code=400, detail="User is already part of this chore")
    
    # Add person to chore
    new_person = Person(
        id=str(uuid4()), 
        name=target_user.full_name,
        user_id=target_user.id
    )
    chore.people.append(new_person)
    redis_service.save_chore(chore)
    
    # Add chore to target user's chore list
    if chore_id not in target_user.chore_ids:
        target_user.chore_ids.append(chore_id)
        auth_service.update_user(target_user)
    
    # Get all current participants for broadcast
    participant_ids = [person.user_id for person in chore.people]
    
    # Broadcast update to all participants
    redis_service.publish_update({
        "type": "person_added",
        "chore_id": chore_id,
        "chore": chore.dict(),
        "person": new_person.dict(),
        "participants": participant_ids
    })
    
    return chore

@router.delete("/{chore_id}/people/{person_id}", response_model=Chore)
async def remove_person_from_chore(
    chore_id: str, 
    person_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove a person from a chore"""
    from app.services.auth_service import auth_service
    
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if current user has access to this chore
    if not any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(status_code=403, detail="You don't have access to this chore")
    
    # Find the person to remove
    person_index = None
    removed_person = None
    for i, person in enumerate(chore.people):
        if person.id == person_id:
            person_index = i
            removed_person = person
            break
    
    if person_index is None:
        raise HTTPException(status_code=404, detail="Person not found")
    
    # Only allow removing yourself or if you're the creator
    if (current_user.id != removed_person.user_id and 
        chore.created_by != current_user.id):
        raise HTTPException(status_code=403, detail="You can only remove yourself or if you're the creator")
    
    # Remove person from chore
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
    
    # Remove chore from removed user's chore list
    removed_user = auth_service.get_user_by_id(removed_person.user_id)
    if removed_user and chore_id in removed_user.chore_ids:
        removed_user.chore_ids.remove(chore_id)
        auth_service.update_user(removed_user)
    
    # Get remaining participants for broadcast
    participant_ids = [person.user_id for person in chore.people]
    
    # Broadcast update to remaining participants
    redis_service.publish_update({
        "type": "person_removed",
        "chore_id": chore_id,
        "chore": chore.dict(),
        "removed_person": removed_person.dict(),
        "participants": participant_ids
    })
    
    return chore

@router.post("/{chore_id}/advance", response_model=Chore)
async def advance_queue(chore_id: str, current_user: User = Depends(get_current_user)):
    """Advance to the next person in the queue"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if current user has access to this chore
    if not any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(status_code=403, detail="You don't have access to this chore")
    
    if len(chore.people) == 0:
        raise HTTPException(status_code=400, detail="No people in chore")
    
    # Advance to next person
    chore.current_person_index = (chore.current_person_index + 1) % len(chore.people)
    redis_service.save_chore(chore)
    
    # Get all participants for broadcast
    participant_ids = [person.user_id for person in chore.people]
    
    # Broadcast update to all participants
    redis_service.publish_update({
        "type": "queue_advanced",
        "chore_id": chore_id,
        "chore": chore.dict(),
        "new_current_person": chore.people[chore.current_person_index].dict(),
        "participants": participant_ids
    })
    
    return chore

@router.post("/{chore_id}/leave")
async def leave_chore(chore_id: str, current_user: User = Depends(get_current_user)):
    """Leave a chore"""
    chore = redis_service.get_chore(chore_id)
    if not chore:
        raise HTTPException(status_code=404, detail="Chore not found")
    
    # Check if current user is in this chore
    if not any(person.user_id == current_user.id for person in chore.people):
        raise HTTPException(status_code=400, detail="You are not part of this chore")
    
    # Find user's person entry in the chore
    person_to_remove = None
    for person in chore.people:
        if person.user_id == current_user.id:
            person_to_remove = person
            break
    
    if person_to_remove:
        # Use the existing remove person endpoint logic
        await remove_person_from_chore(chore_id, person_to_remove.id, current_user)
    
    return {"message": "Successfully left the chore"}