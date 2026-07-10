import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import Request, Response
from sse_starlette.sse import EventSourceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SSEManager:
    def __init__(self):
        self.clients: Dict[str, asyncio.Queue] = {}
        self.client_counter = 0
    
    async def add_client(self, request: Request) -> str:
        """
        Add a new client to the SSE manager
        """
        client_id = f"client_{self.client_counter}"
        self.client_counter += 1
        
        # Create queue for this client
        self.clients[client_id] = asyncio.Queue()
        
        logger.info(f"Added new SSE client: {client_id}")
        return client_id
    
    def remove_client(self, client_id: str):
        """
        Remove a client from the SSE manager
        """
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"Removed SSE client: {client_id}")
    
    async def broadcast_data(self, data: Dict[str, Any], event_type: str = "data"):
        """
        Broadcast data to all connected clients
        """
        if self.clients:
            # Create message
            message = {
                "event": event_type,
                "data": data,
                "id": asyncio.get_event_loop().time()
            }
            
            # Send to all clients
            await asyncio.gather(
                *[client_queue.put(message) for client_queue in self.clients.values()]
            )
    
    async def stream_events(self, request: Request, client_id: str):
        """
        Stream events to a specific client
        """
        try:
            while True:
                if client_id not in self.clients:
                    break
                
                # Wait for data with timeout
                try:
                    data = await asyncio.wait_for(
                        self.clients[client_id].get(), 
                        timeout=30.0
                    )
                    yield data
                except asyncio.TimeoutError:
                    # Send heartbeat
                    yield {
                        "event": "heartbeat",
                        "data": "",
                        "id": asyncio.get_event_loop().time()
                    }
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for client {client_id}")
        finally:
            self.remove_client(client_id)

# Global SSE manager instance
sse_manager = SSEManager()

# Example usage
if __name__ == "__main__":
    # This would be integrated with FastAPI routes
    pass