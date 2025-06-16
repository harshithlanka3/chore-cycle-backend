from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.websocket_service import websocket_manager
import json

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # You can handle client messages here if needed
            # For now, we'll just echo back a confirmation
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket_manager.send_personal_message(
                    json.dumps({"type": "pong"}), 
                    websocket
                )
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)