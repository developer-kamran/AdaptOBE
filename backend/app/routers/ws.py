from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.models.user import User, UserRole
from app.services import course_service
from app.services.exceptions import NotFoundError, PermissionDeniedError

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])

# WS 1008 = "Policy Violation", the closest standard code to 401/403 for sockets.
POLICY_VIOLATION = 1008


async def forward_to_websockets(event: dict) -> None:
    """notifications.py subscriber that fans a recalculation event out to
    whichever browsers currently have that course's dashboard open.
    """
    if event.get("type") == "attainment.recalculated" and "course_id" in event:
        await manager.broadcast(event["course_id"], event)


async def _authenticate(token: str | None) -> User | None:
    """Mirrors get_current_user, but native WebSocket cannot carry an
    Authorization header from browser JS -- the token arrives as a query param.
    """
    if not token:
        return None

    try:
        payload = decode_token(token)
    except ValueError:
        return None

    if payload.get("type") != "access":
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(payload["sub"])))
        user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        return None
    return user


@router.websocket("/course/{course_id}")
async def course_updates(websocket: WebSocket, course_id: int, token: str | None = None):
    """Push a message whenever this course's attainment is recalculated.

    Clients connect with `?token=<access_token>`; the connection is refused
    (matching the REST endpoints' RBAC) if the token is missing/invalid, the
    role isn't faculty, or the faculty user doesn't own the course.
    """
    user = await _authenticate(token)
    if user is None:
        await websocket.close(code=POLICY_VIOLATION)
        return
    if user.role != UserRole.faculty:
        await websocket.close(code=POLICY_VIOLATION)
        return

    async with AsyncSessionLocal() as db:
        try:
            await course_service.get_course_for_user(db, course_id, user)
        except (NotFoundError, PermissionDeniedError):
            await websocket.close(code=POLICY_VIOLATION)
            return

    await manager.connect(course_id, websocket)
    try:
        while True:
            # This endpoint is server-push only; draining the socket just
            # lets us detect the client disconnecting.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(course_id, websocket)
