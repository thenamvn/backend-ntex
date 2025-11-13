from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
import json


class ConnectionManager:
    """
    Manages WebSocket connections for real-time notifications.
    
    Maintains active connections per user and broadcasts messages
    to specific users or all connected clients.
    """
    
    def __init__(self):
        # Dictionary mapping user_id to list of WebSocket connections
        # A user can have multiple connections (e.g., multiple devices)
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection to add
            user_id: ID of the user connecting
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        
        self.active_connections[user_id].append(websocket)
        print(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
            user_id: ID of the user disconnecting
        """
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Clean up empty connection lists
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        print(f"User {user_id} disconnected. Remaining connections: {len(self.active_connections.get(user_id, []))}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: Message data to send (will be JSON encoded)
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
    
    async def broadcast_to_user(self, user_id: int, message: dict):
        """
        Broadcast a message to all connections of a specific user.
        
        Args:
            user_id: Target user ID
            message: Message data to broadcast (will be JSON encoded)
        """
        if user_id not in self.active_connections:
            print(f"No active connections for user {user_id}")
            return
        
        # Send to all connections for this user
        disconnected = []
        for connection in self.active_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, user_id)
    
    async def broadcast_to_all(self, message: dict):
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message data to broadcast (will be JSON encoded)
        """
        for user_id, connections in self.active_connections.items():
            await self.broadcast_to_user(user_id, message)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """
        Get the number of active connections for a user.
        
        Args:
            user_id: User ID to check
        
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(user_id, []))
    
    def get_total_connections(self) -> int:
        """
        Get the total number of active connections across all users.
        
        Returns:
            Total connection count
        """
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_connected_users(self) -> List[int]:
        """
        Get a list of all currently connected user IDs.
        
        Returns:
            List of user IDs with active connections
        """
        return list(self.active_connections.keys())


# Singleton instance
connection_manager = ConnectionManager()
