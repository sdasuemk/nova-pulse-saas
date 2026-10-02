from typing import Dict, Set
from fastapi import WebSocket
from app.core.logging import logger


class ConnectionManager:
    """
    Manages active WebSocket connections grouped by tenant_id.
    Ensures complete tenant isolation: messages broadcast to one tenant
    never leak to other tenants.
    """

    def __init__(self) -> None:
        # tenant_id -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, tenant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = set()
        self.active_connections[tenant_id].add(websocket)
        logger.info(f"WebSocket connected to tenant '{tenant_id}'. Total: {len(self.active_connections[tenant_id])}")

    def disconnect(self, tenant_id: str, websocket: WebSocket) -> None:
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].discard(websocket)
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
        logger.info(f"WebSocket disconnected from tenant '{tenant_id}'.")

    async def broadcast_to_tenant(self, tenant_id: str, event_type: str, data: dict) -> None:
        """Broadcasts a JSON payload to all active clients of a tenant."""
        if tenant_id not in self.active_connections:
            return

        message = {
            "tenant_id": tenant_id,
            "event": event_type,
            "payload": data,
        }

        dead_connections = set()
        for connection in list(self.active_connections[tenant_id]):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WS message: {e}")
                dead_connections.add(connection)

        # Cleanup dropped connections
        for dead in dead_connections:
            self.disconnect(tenant_id, dead)


ws_manager = ConnectionManager()
