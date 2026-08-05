"""WebSocket auth-gate tests plus a pure-Python unit test of ConnectionManager.

The rejection paths below need no database access, so they're safe to drive
through Starlette's (sync, separate-loop) TestClient. A full authenticated
round-trip needs `_authenticate` to see a user committed on a connection our
transactional test fixtures deliberately never commit -- that path is instead
verified live against a running server (see the Module 4 completion notes).
"""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.ws_manager import ConnectionManager
from app.main import app


def test_ws_rejects_missing_token():
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with TestClient(app).websocket_connect("/api/v1/ws/course/1"):
            pass
    assert exc_info.value.code == 1008


def test_ws_rejects_garbage_token():
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with TestClient(app).websocket_connect("/api/v1/ws/course/1?token=not-a-jwt"):
            pass
    assert exc_info.value.code == 1008


class _FakeSocket:
    def __init__(self, fail=False):
        self.fail = fail
        self.accepted = False
        self.sent = []

    async def accept(self):
        self.accepted = True

    async def send_json(self, message):
        if self.fail:
            raise RuntimeError("connection reset")
        self.sent.append(message)


async def test_connection_manager_broadcasts_to_all_sockets_for_a_course():
    manager = ConnectionManager()
    a, b = _FakeSocket(), _FakeSocket()
    await manager.connect(1, a)
    await manager.connect(1, b)

    await manager.broadcast(1, {"type": "attainment.recalculated", "course_id": 1})

    assert a.sent == [{"type": "attainment.recalculated", "course_id": 1}]
    assert b.sent == [{"type": "attainment.recalculated", "course_id": 1}]


async def test_connection_manager_only_broadcasts_to_the_matching_course():
    manager = ConnectionManager()
    for_course_1, for_course_2 = _FakeSocket(), _FakeSocket()
    await manager.connect(1, for_course_1)
    await manager.connect(2, for_course_2)

    await manager.broadcast(1, {"type": "attainment.recalculated", "course_id": 1})

    assert len(for_course_1.sent) == 1
    assert for_course_2.sent == []


async def test_connection_manager_drops_failing_socket_without_breaking_others():
    """A dead socket for one browser tab must not stop the broadcast to others."""
    manager = ConnectionManager()
    healthy, dead = _FakeSocket(), _FakeSocket(fail=True)
    await manager.connect(1, healthy)
    await manager.connect(1, dead)

    await manager.broadcast(1, {"type": "attainment.recalculated", "course_id": 1})

    assert len(healthy.sent) == 1
