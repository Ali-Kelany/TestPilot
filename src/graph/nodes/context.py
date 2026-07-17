"""Shared context for all graph nodes.

Created once per agent invocation and injected into every node via
constructor.  Intentionally immutable: everything that changes during
execution lives in AgentState, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from typing import Any

from src.domain.events import Event
from src.infrastructure.browser import Browser
from src.services.event_bus import EventBus


@dataclass(frozen=True)
class NodeContext:
    """Immutable bag of dependencies shared by all graph nodes.

    frozen=True enforces the invariant: nothing here changes during
    a test run.  Per-step mutable values (step_start_time, loop counter)
    live in AgentState where they belong.
    """

    browser: Browser
    logger: Logger
    event_bus: EventBus | None
    session_id: str

    actor_model: Any
    assertor_model: Any
    recovery_model: Any

    max_action_loops: int = 16
    max_step_retries: int = 3

    async def emit(self, event: Event) -> None:
        """Emit an event if an event bus is attached."""
        if self.event_bus is not None:
            await self.event_bus.emit(event)
