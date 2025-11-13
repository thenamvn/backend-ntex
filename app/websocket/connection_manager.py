from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
import json

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection and send initial data."""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        print(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
        
        # 🚀 Send initial health data when connected
        await self._send_initial_data(websocket, user_id)
    
    async def _send_initial_data(self, websocket: WebSocket, user_id: int):
        """
        Send the latest health data to newly connected client.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
        """
        try:
            # Import here to avoid circular dependency
            from ..services.health_service import health_service
            from ..db.database import SessionLocal
            
            # Get latest health record
            db = SessionLocal()
            try:
                history = health_service.get_user_health_history(
                    db=db,
                    user_id=user_id,
                    limit=1
                )
                
                if history:
                    latest = history[0]
                    message = {
                        "event": "INITIAL_DATA",
                        "data": {
                            "id": latest.id,
                            "temperature": latest.temperature,
                            "humidity": latest.humidity,
                            "cry_detected": latest.cry_detected,
                            "sick_detected": latest.sick_detected,
                            "created_at": latest.created_at.isoformat(),
                            "notes": latest.notes
                        }
                    }
                    await websocket.send_json(message)
                    print(f"📤 Sent initial data to user {user_id}")
                else:
                    # No data yet, send welcome message
                    await websocket.send_json({
                        "event": "CONNECTED",
                        "message": "Connected successfully. Waiting for health data..."
                    })
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error sending initial data: {e}")
            # Still send a basic connection message
            try:
                await websocket.send_json({
                    "event": "CONNECTED",
                    "message": "Connected successfully"
                })
            except:
                pass
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """Remove a WebSocket connection."""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Clean up empty lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        print(f"User {user_id} disconnected")
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        """
        Broadcast a message to all connections of a specific user.
        
        Args:
            user_id: Target user ID
            message: Message dict to send
        """
        if user_id not in self.active_connections:
            print(f"No active connections for user {user_id}")
            return
        
        # Send to all connections of this user
        disconnected = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                print(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, user_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.broadcast_to_user(user_id, message)


connection_manager = ConnectionManager()