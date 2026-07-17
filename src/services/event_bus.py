"""Async event bus for decoupled event handling.

The only public registration API is :meth:`EventBus.subscribe`, which
returns an unsubscribe callable.  Decorator shortcuts are intentionally
omitted to prevent handler leaks (e.g. registering inside a request
handler without ever unsubscribing).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Set, TypeAlias

from src.domain.events import Event, EventType

logger = logging.getLogger(__name__)

AsyncEventHandler: TypeAlias = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Async pub/sub event bus.

    Features
    --------
    - Subscribe to a specific :class:`EventType` or to *all* events.
    - ``subscribe()`` returns an **unsubscribe** callable — the only safe API.
    - Handlers execute concurrently via :func:`asyncio.gather`.
    - A failing handler is logged but never prevents other handlers from running.

    Usage::

        bus = EventBus()

        unsub = bus.subscribe(my_handler, EventType.STEP_STARTED)
        await bus.emit(StepStartedEvent(...))
        unsub()                          # clean removal
    """

    __slots__ = ("_handlers", "_global_handlers", "_error_handlers")

    def __init__(self) -> None:
        self._handlers: dict[EventType, Set[AsyncEventHandler]] = defaultdict(set)
        self._global_handlers: Set[AsyncEventHandler] = set()
        self._error_handlers: Set[Callable[[Event, Exception], Awaitable[None]]] = set()

    def subscribe(
        self,
        handler: AsyncEventHandler,
        event_type: EventType | None = None,
    ) -> Callable[[], None]:
        """Register *handler* for *event_type* (or all events if ``None``).

        Returns a zero-argument callable that removes the subscription.
        """
        if event_type is None:
            self._global_handlers.add(handler)
            return lambda: self._global_handlers.discard(handler)

        self._handlers[event_type].add(handler)
        return lambda: self._handlers[event_type].discard(handler)

    def on_error(
        self,
        handler: Callable[[Event, Exception], Awaitable[None]],
    ) -> Callable[[], None]:
        """Subscribe to handler errors.  Returns an unsubscribe callable."""
        self._error_handlers.add(handler)
        return lambda: self._error_handlers.discard(handler)

    async def emit(self, event: Event) -> None:
        """Emit *event* to every matching subscriber.

        Handlers run concurrently.  Failures are caught, logged, and
        forwarded to error handlers — they never propagate to the caller.
        """
        handlers: list[AsyncEventHandler] = []
        handlers.extend(self._global_handlers)
        handlers.extend(self._handlers.get(event.type, set()))

        if not handlers:
            return

        results = await asyncio.gather(
            *[self._invoke(h, event) for h in handlers],
            return_exceptions=True,
        )

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                await self._handle_error(event, result, handler)

    def clear(self, event_type: EventType | None = None) -> None:
        """Remove subscriptions.

        If *event_type* is ``None`` every subscription is removed.
        """
        if event_type is None:
            self._handlers.clear()
            self._global_handlers.clear()
        else:
            self._handlers[event_type].clear()

    @property
    def handler_count(self) -> int:
        """Total number of registered handlers (typed + global)."""
        return len(self._global_handlers) + sum(
            len(h) for h in self._handlers.values()
        )

    async def _invoke(self, handler: AsyncEventHandler, event: Event) -> None:
        import inspect
        result = handler(event)
        if inspect.isawaitable(result):
            await result

    async def _handle_error(
        self,
        event: Event,
        error: Exception,
        handler: AsyncEventHandler,
    ) -> None:
        handler_name = getattr(handler, "__name__", str(handler))
        logger.error(
            "Event handler '%s' failed for %s: %s",
            handler_name,
            event.type.value,
            error,
            exc_info=error,
        )

        for error_handler in self._error_handlers:
            try:
                await error_handler(event, error)
            except Exception as exc:
                logger.error("Error handler failed: %s", exc, exc_info=exc)