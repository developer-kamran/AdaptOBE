"""Recalculation event fan-out.

Section 8 requires that a recalculation broadcast a notification. The transport
itself (native FastAPI WebSockets) is Module 4's job, so this module owns only
the seam: subscribers register here, and Module 4 will register a WebSocket
connection manager against it without the attainment engine changing.
"""

import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

Subscriber = Callable[[dict], Awaitable[None]]

_subscribers: list[Subscriber] = []


def subscribe(subscriber: Subscriber) -> None:
    _subscribers.append(subscriber)


def unsubscribe(subscriber: Subscriber) -> None:
    if subscriber in _subscribers:
        _subscribers.remove(subscriber)


async def broadcast(event: dict) -> None:
    """Deliver an event to every subscriber.

    A failing subscriber must never roll back or break the calculation that
    produced the event, so exceptions are logged and swallowed.
    """
    logger.info("Broadcasting event: %s", event.get("type"))

    for subscriber in list(_subscribers):
        try:
            await subscriber(event)
        except Exception:  # noqa: BLE001 - a bad listener must not break scoring
            logger.exception("Subscriber failed handling event %s", event.get("type"))
