from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .config import settings
from .db.database import create_db_and_tables
from .routers import auth_router, health_router
from .websocket import connection_manager
from .services import get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup and shutdown.
    """
    # Startup
    print("🚀 Starting Baby Health Monitoring API...")
    
    # Create database tables
    print("📊 Creating database tables...")
    create_db_and_tables()
    
    # Ensure upload directory exists
    os.makedirs(settings.upload_dir, exist_ok=True)
    print(f"📁 Upload directory ready: {settings.upload_dir}")
    
    # Ensure models directory exists
    os.makedirs(os.path.dirname(settings.cry_model_path), exist_ok=True)
    print(f"🤖 AI models directory ready: {settings.cry_model_path}")

    print("✅ Application started successfully!")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Baby Health Monitoring API...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Backend API for Baby Health Monitoring with AI Cry Detection",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(health_router)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "app": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "auth": "/auth",
            "health": "/health",
            "websocket": "/ws/{user_id}"
        }
    }


@app.get("/health-check")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "database": "connected",
        "websocket_connections": connection_manager.get_total_connections(),
        "connected_users": len(connection_manager.get_connected_users())
    }


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(..., description="JWT token for authentication")
):
    """
    WebSocket endpoint for real-time notifications.
    
    **Connection:**
    - URL: `ws://localhost:8000/ws/{user_id}?token=<jwt_token>`
    - Requires JWT token for authentication
    
    **Events Received:**
    - `CRY_DETECTED`: Baby crying detected with illness status
    - `HEALTH_UPDATE`: General health status updates
    
    **Message Format:**
    ```json
    {
        "event": "CRY_DETECTED",
        "sick_detected": true,
        "timestamp": "2025-11-13T10:30:00Z"
    }
    ```
    
    **Usage:**
    1. Connect with user_id and valid JWT token
    2. Listen for incoming messages
    3. Handle events in your mobile app (show alerts, notifications, etc.)
    """
    # Note: In production, you should validate the token here
    # For now, we'll accept any connection for simplicity
    # You can add token validation using get_current_user with token
    
    await connection_manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        await connection_manager.send_personal_message(
            {
                "event": "CONNECTED",
                "message": f"Connected to Baby Health Monitoring",
                "user_id": user_id
            },
            websocket
        )
        
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            # Echo back for testing
            await connection_manager.send_personal_message(
                {
                    "event": "ECHO",
                    "message": f"Received: {data}"
                },
                websocket
            )
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, user_id)
        print(f"User {user_id} disconnected from WebSocket")
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        connection_manager.disconnect(websocket, user_id)


# Development mode info
if __name__ == "__main__":
    import uvicorn
    print("🔧 Running in development mode")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔌 WebSocket: ws://localhost:8000/ws/{user_id}?token=<jwt_token>")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
