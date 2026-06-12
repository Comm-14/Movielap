from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, list[WebSocket]] = defaultdict(list)

    async def connect(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id].append(websocket)

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        session_connections = self._connections.get(session_id, [])
        if websocket in session_connections:
            session_connections.remove(websocket)
        if not session_connections and session_id in self._connections:
            del self._connections[session_id]

    async def broadcast(self, session_id: UUID, payload: dict[str, Any]) -> None:
        stale_connections: list[WebSocket] = []
        for connection in self._connections.get(session_id, []):
            try:
                await connection.send_json(payload)
            except Exception:
                stale_connections.append(connection)

        for stale_connection in stale_connections:
            self.disconnect(session_id, stale_connection)


connection_manager = ConnectionManager()
