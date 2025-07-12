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
            # Create async Redis client with same config as redis_service
            self.redis_client = redis.Redis(
                host=redis_service.redis_client.connection_pool.connection_kwargs.get('host'),
                port=redis_service.redis_client.connection_pool.connection_kwargs.get('port'),
                password=redis_service.redis_client.connection_pool.connection_kwargs.get('password'),
                decode_responses=True
            )
            asyncio.create_task(self.redis_subscriber())
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending message to websocket: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast(self, message: str):
        if not self.active_connections:
            return
            
        connections_copy = self.active_connections.copy()
        
        for connection in connections_copy:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                if connection in self.active_connections:
                    self.active_connections.remove(connection)
    
    async def redis_subscriber(self):
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("chore_updates")
            print("Successfully subscribed to Redis pub/sub")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    print(f"Broadcasting message: {message['data']}")
                    await self.broadcast(message["data"])
        except Exception as e:
            print(f"Redis subscriber error: {e}")

websocket_manager = WebSocketManager()