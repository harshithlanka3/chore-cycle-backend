from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auths, chores, websockets
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Chore Management API", 
    version="1.0.0",
    description="Real-time chore management with WebSocket support and user authentication"
)

# CORS middleware for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auths.router, prefix="/api")
app.include_router(chores.router, prefix="/api")
app.include_router(websockets.router)

@app.get("/")
async def root():
    return {
        "message": "Chore Management API",
        "docs": "/docs",
        "websocket": "/ws",
        "auth": "/api/auth"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}