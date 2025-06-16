from fastapi import WebSocket
from typing import List, Dict
import json
import asyncio
import redis.asyncio as redis
from app.services.redis_service import redis_service

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.redis_client = None
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Start Redis subscriber if not already started
        if not self.redis_client:
            self.redis_client = redis.Redis(decode_responses=True)
            asyncio.create_task(self.redis_subscriber())
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)
    
    async def redis_subscriber(self):
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("chore_updates")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                await self.broadcast(message["data"])

websocket_manager = WebSocketManager()