from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.services.websocket_service import websocket_manager
from app.services.auth_service import current_active_user
from app.models.user import User
import json

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # For WebSocket authentication, we'll need to handle it differently
    # since we can't use the normal Depends() mechanism
    await websocket_manager.connect(websocket, None)  # Initially connect without user
    user_id = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle authentication message
            if message.get("type") == "auth":
                token = message.get("token")
                if token:
                    # Validate token and get user_id
                    # This is a simplified version - you'd need proper token validation
                    try:
                        # Add your token validation logic here
                        user_id = message.get("user_id")  # Temporarily simplified
                        await websocket_manager.send_to_user(
                            json.dumps({"type": "auth_success"}), 
                            user_id
                        )
                    except:
                        await websocket.send_text(json.dumps({"type": "auth_failed"}))
            
            elif message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        if user_id:
            websocket_manager.disconnect(websocket, user_id)
        else:
            # Handle unauthenticated disconnect
            pass