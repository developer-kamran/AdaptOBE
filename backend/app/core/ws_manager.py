"""In-process WebSocket connection registry, keyed by course id.

Single-process only: fine for local development and a single Uvicorn worker.
Scaling to multiple workers would need a shared pub/sub (e.g. Redis) behind
this same interface -- callers don't need to change.
"""

import logging
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, course_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[course_id].add(websocket)

    def disconnect(self, course_id: int, websocket: WebSocket) -> None:
        self._connections[course_id].discard(websocket)
        if not self._connections[course_id]:
            del self._connections[course_id]

    async def broadcast(self, course_id: int, message: dict) -> None:
        for websocket in list(self._connections.get(course_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # noqa: BLE001 - one dead socket must not break the rest
                logger.exception("Failed to send WebSocket message; dropping connection")
                self.disconnect(course_id, websocket)


manager = ConnectionManager()
