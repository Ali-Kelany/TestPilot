"""Execution service — orchestrates a test run with event emission.

The service owns the lifecycle (browser, graph) and emits
``ExecutionStartedEvent`` / ``ExecutionCompletedEvent``.  Fine-grained
events (steps, tools, verification) are emitted by individual graph
nodes via the shared :class:`EventBus`.

All log output goes through the module logger; per-session structured
log entries are persisted by the :class:`DatabaseListener` via
``RunLogEntry`` rows — no filesystem log files are created.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from src.config import ExecutionConfig, Settings
from src.domain.events import (
    ErrorEvent,
    ExecutionCompletedEvent,
    ExecutionStartedEvent,
    LogEvent,
    StepCompletedEvent,
    EventType,
)
from src.domain.test_case import TestCase
from src.graph.agent import create_agent
from src.graph.nodes.token_tracker import TokenTracker
from src.graph.state import create_initial_state
from src.infrastructure.browser import Browser
from src.infrastructure.llm.providers import ModelProvider
from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class EventBusLogHandler(logging.Handler):
    """Bridge standard logging to the EventBus as LogEvents."""

    def __init__(self, bus: EventBus, session_id: str) -> None:
        super().__init__()
        self._bus = bus
        self._session_id = session_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            step_index = getattr(record, "step_index", None)
            event = LogEvent(
                session_id=self._session_id,
                level=record.levelname,
                message=msg,
                source=record.name,
                step_index=step_index,
            )
            # Fire and forget emission (Handler.emit must be sync)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._bus.emit(event))
            except RuntimeError:
                # No running loop (e.g. in a thread or cleanup)
                pass
        except Exception:
            self.handleError(record)


@dataclass
class ExecutionResult:
    """Final outcome of a test execution."""

    session_id: str
    result: str  # passed | failed | error
    duration_seconds: float
    steps_completed: int
    steps_passed: int
    steps_failed: int
    log: list[str]
    error: str | None = None
    total_tokens: int = 0


class ExecutionService:
    """Execute a :class:`TestCase` against a real browser.

    Events are emitted through the injected :class:`EventBus` so that
    any number of consumers (CLI, database listener, WebSocket) can
    react without coupling.

    Usage::

        bus = EventBus()
        settings = Settings()
        service = ExecutionService(bus, settings)

        result = await service.execute(test_case, config)
    """

    def __init__(self, event_bus: EventBus, settings: Settings) -> None:
        self._bus = event_bus
        self._settings = settings

    async def execute(
        self,
        test_case: TestCase,
        config: ExecutionConfig | None = None,
    ) -> ExecutionResult:
        """Run *test_case* end-to-end and return an :class:`ExecutionResult`.

        Args:
            test_case: The domain test case to execute.
            config: Per-run settings (provider, headless …).

        Returns:
            An :class:`ExecutionResult` summarising the run.
        """
        config = config or ExecutionConfig()
        session_id = str(uuid.uuid4())
        start_time = time.time()

        # Use a session-scoped logger that goes to the root logging handlers.
        # The DatabaseListener will persist structured entries via RunLogEntry.
        session_logger = logging.getLogger(f"session.{session_id[:8]}")
        session_logger.setLevel(logging.INFO)
        log_handler = EventBusLogHandler(self._bus, session_id)
        session_logger.addHandler(log_handler)

        # ── lifecycle: started ──────────────────────────────────
        await self._bus.emit(
            ExecutionStartedEvent(
                session_id=session_id,
                test_case_id=test_case.id,
                test_case_name=test_case.name,
                test_case_url=test_case.url,
                total_steps=len(test_case),
                steps=[{"action": s.action, "assertion": s.assertion} for s in test_case.steps],
                provider=config.provider,
                model=config.model or "default",
                headless=config.headless,
            )
        )

        browser: Browser | None = None
        final_state: dict[str, Any] = {}
        error_message: str | None = None
        steps_passed = 0
        steps_failed = 0

        async def on_step_completed(event: StepCompletedEvent):
            nonlocal steps_passed, steps_failed
            if event.session_id == session_id:
                if event.passed:
                    steps_passed += 1
                else:
                    steps_failed += 1

        unsub = None
        token_tracker = TokenTracker()
        try:
            unsub = self._bus.subscribe(on_step_completed, EventType.STEP_COMPLETED)
            browser = await Browser.create(
                logger=session_logger,
                config=config.to_browser_config(),
            )

            await browser.goto(test_case.url)

            provider = ModelProvider(config.provider)
            graph = create_agent(
                browser=browser,
                logger=session_logger,
                settings=self._settings,
                event_bus=self._bus,
                session_id=session_id,
                provider=provider,
                model=config.model,
                token_tracker=token_tracker,
            )

            initial_state = create_initial_state(test_case)

            async for state in graph.astream(
                initial_state,
                config={"recursion_limit": config.recursion_limit},
                stream_mode="values",
            ):
                final_state = state

        except Exception as e:
            error_message = str(e)
            session_logger.exception("Execution failed: %s", e)
            await self._bus.emit(
                ErrorEvent(
                    session_id=session_id,
                    error_type=type(e).__name__,
                    message=str(e),
                    recoverable=False,
                )
            )

        finally:
            if unsub:
                unsub()
            session_logger.removeHandler(log_handler)
            if browser:
                await browser.close()

        # ── compute results ─────────────────────────────────────
        duration = time.time() - start_time
        result = final_state.get(
            "result", "error" if error_message else "unknown"
        )
        log_entries: list[str] = final_state.get("log", [])

        if test_case.type == "N":
            if result == "failed":
                result = "passed"
                final_state["result"] = "passed"
                log_entries.append("TEST PASSED: Negative test case failed as expected.")
            elif result == "passed":
                result = "failed"
                final_state["result"] = "failed"
                log_entries.append("TEST FAILED: Negative test case did not fail as expected.")

        steps_completed = final_state.get("step_index", 1) - 1
        total_tokens = token_tracker.total_tokens

        # ── lifecycle: completed ────────────────────────────────
        await self._bus.emit(
            ExecutionCompletedEvent(
                session_id=session_id,
                result=result,
                duration_seconds=duration,
                steps_completed=steps_completed,
                steps_passed=steps_passed,
                steps_failed=steps_failed,
                final_log=log_entries,
                total_tokens=total_tokens,
            )
        )

        return ExecutionResult(
            session_id=session_id,
            result=result,
            duration_seconds=duration,
            steps_completed=steps_completed,
            steps_passed=steps_passed,
            steps_failed=steps_failed,
            log=log_entries,
            error=error_message,
            total_tokens=total_tokens,
        )
