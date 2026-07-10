import asyncio
import logging
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connection established. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except WebSocketDisconnect:
            self.disconnect(websocket)
            logger.warning("WebSocket disconnected during message send")
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients
        """
        if self.active_connections:
            await asyncio.gather(
                *[self.send_personal_message(message, connection) for connection in self.active_connections]
            )
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """
        Broadcast an alert to all connected clients
        """
        alert_message = {
            "type": "alert",
            "data": alert_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.broadcast(alert_message)

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

# Example usage
if __name__ == "__main__":
    # This would be integrated with FastAPI routes
    pass