from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chores, websockets, auth
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Chore Management API", 
    version="1.0.0",
    description="Real-time chore management with user authentication"
)

# CORS middleware for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth")
app.include_router(chores.router, prefix="/api")
app.include_router(websockets.router)

@app.get("/")
async def root():
    return {
        "message": "Chore Management API with Authentication",
        "docs": "/docs",
        "auth": "/auth",
        "websocket": "/ws"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}