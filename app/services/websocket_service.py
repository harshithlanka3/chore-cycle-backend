from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio
import redis.asyncio as redis
from app.services.redis_service import redis_service

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # user_id -> connections
        self.redis_client = None
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        # Start Redis subscriber if not already started
        if not self.redis_client:
            self.redis_client = redis.Redis(decode_responses=True)
            asyncio.create_task(self.redis_subscriber())
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                conn for conn in self.active_connections[user_id] if conn != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_to_user(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id][:]:  # Copy list to avoid modification during iteration
                try:
                    await connection.send_text(message)
                except:
                    # Remove dead connections
                    self.active_connections[user_id].remove(connection)
    
    async def send_to_chore_participants(self, message: str, chore_id: str):
        """Send message only to users who have access to this chore"""
        chore = redis_service.get_chore_by_id(chore_id)
        if not chore:
            return
            
        # Get all users who should receive this update
        target_users = {chore.owner_id} | set(chore.shared_with)
        
        for user_id in target_users:
            await self.send_to_user(message, user_id)
    
    async def broadcast(self, message: str):
        """Broadcast to all connected users"""
        for user_connections in self.active_connections.values():
            for connection in user_connections[:]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove dead connections
                    user_connections.remove(connection)
    
    async def redis_subscriber(self):
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("chore_updates")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    update_data = json.loads(message["data"])
                    chore_id = update_data.get("chore_id")
                    
                    if chore_id:
                        # Send only to chore participants
                        await self.send_to_chore_participants(message["data"], chore_id)
                    else:
                        # Fallback to broadcast for messages without chore_id
                        await self.broadcast(message["data"])
                except json.JSONDecodeError:
                    # Fallback to broadcast for non-JSON messages
                    await self.broadcast(message["data"])

websocket_manager = WebSocketManager()