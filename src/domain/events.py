"""Event definitions emitted during test execution.

Every event is an immutable dataclass with:
- ``type``         – discriminator enum
- ``session_id``   – correlates all events from one run
- ``timestamp``    – UTC creation time
- ``event_id``     – unique short id
- ``to_dict()``    – JSON-safe serialisation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(Enum):
    """Discriminator for every event kind."""

    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"

    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"

    OBSERVATION = "agent.observation"
    TOOL_CALLED = "agent.tool.called"
    TOOL_RESULT = "agent.tool.result"

    VERIFICATION = "verification"
    RECOVERY = "recovery"

    LOG = "log"
    ERROR = "error"


@dataclass(kw_only=True)
class Event:
    """Base class for all events."""

    type: EventType
    session_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        base: dict[str, Any] = {
            "type": self.type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
        }
        base.update(self._payload())
        return base

    def _payload(self) -> dict[str, Any]:
        """Override in subclasses to add event-specific fields."""
        return {}


@dataclass(kw_only=True)
class ExecutionStartedEvent(Event):
    """Emitted when test execution begins."""

    type: EventType = field(default=EventType.EXECUTION_STARTED, init=False)
    test_case_id: str = ""
    test_case_name: str = ""
    test_case_url: str = ""
    total_steps: int = 0
    steps: list[dict[str, str]] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    headless: bool = True

    def _payload(self) -> dict[str, Any]:
        return {
            "test_case": {
                "id": self.test_case_id,
                "name": self.test_case_name,
                "url": self.test_case_url,
                "total_steps": self.total_steps,
                "steps": self.steps,
            },
            "config": {
                "provider": self.provider,
                "model": self.model,
                "headless": self.headless,
            },
        }


@dataclass(kw_only=True)
class ExecutionCompletedEvent(Event):
    """Emitted when test execution finishes."""

    type: EventType = field(default=EventType.EXECUTION_COMPLETED, init=False)
    result: str = ""  # passed | failed | error
    duration_seconds: float = 0.0
    steps_completed: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    final_log: list[str] = field(default_factory=list)
    total_tokens: int = 0

    def _payload(self) -> dict[str, Any]:
        return {
            "result": self.result,
            "duration_seconds": round(self.duration_seconds, 2),
            "steps": {
                "completed": self.steps_completed,
                "passed": self.steps_passed,
                "failed": self.steps_failed,
            },
            "log": self.final_log,
            "total_tokens": self.total_tokens,
        }


@dataclass(kw_only=True)
class StepStartedEvent(Event):
    """Emitted when a test step begins."""

    type: EventType = field(default=EventType.STEP_STARTED, init=False)
    step_index: int = 0
    total_steps: int = 0
    action: str = ""
    assertion: str = ""

    def _payload(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "action": self.action,
            "assertion": self.assertion,
        }


@dataclass(kw_only=True)
class StepCompletedEvent(Event):
    """Emitted when a test step finishes.

    ``screenshot_observation`` and ``screenshot_verification`` carry the
    raw image bytes captured during the step so that the DatabaseListener
    can persist them as BLOBs without reading from disk.
    """

    type: EventType = field(default=EventType.STEP_COMPLETED, init=False)
    step_index: int = 0
    passed: bool = False
    reason: str = ""
    retry_count: int = 0
    duration_seconds: float = 0.0
    screenshot_observation: bytes | None = None
    screenshot_verification: bytes | None = None

    def _payload(self) -> dict[str, Any]:
        return {
            "step_index": self.step_index,
            "passed": self.passed,
            "reason": self.reason,
            "retry_count": self.retry_count,
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclass(kw_only=True)
class ObservationEvent(Event):
    """Emitted when the agent observes page state."""

    type: EventType = field(default=EventType.OBSERVATION, init=False)
    page_url: str = ""
    page_title: str = ""
    element_count: int = 0
    screenshot_size: int = 0

    def _payload(self) -> dict[str, Any]:
        return {
            "page": {"url": self.page_url, "title": self.page_title},
            "element_count": self.element_count,
            "screenshot_size": self.screenshot_size,
        }


@dataclass(kw_only=True)
class ToolCalledEvent(Event):
    """Emitted when the agent invokes a tool."""

    type: EventType = field(default=EventType.TOOL_CALLED, init=False)
    tool_name: str = ""
    tool_args: dict[str, Any] = field(default_factory=dict)
    tool_call_id: str = ""

    def _payload(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "tool_call_id": self.tool_call_id,
        }


@dataclass(kw_only=True)
class ToolResultEvent(Event):
    """Emitted when a tool returns a result."""

    type: EventType = field(default=EventType.TOOL_RESULT, init=False)
    tool_name: str = ""
    tool_call_id: str = ""
    result: str = ""
    success: bool = True

    def _payload(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "tool_call_id": self.tool_call_id,
            "result": self.result,
            "success": self.success,
        }


@dataclass(kw_only=True)
class VerificationEvent(Event):
    """Emitted with assertion verification results."""

    type: EventType = field(default=EventType.VERIFICATION, init=False)
    assertion: str = ""
    passed: bool = False
    reason: str = ""
    duration_seconds: float = 0.0

    def _payload(self) -> dict[str, Any]:
        return {
            "assertion": self.assertion,
            "passed": self.passed,
            "reason": self.reason,
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclass(kw_only=True)
class RecoveryEvent(Event):
    """Emitted during recovery decisions."""

    type: EventType = field(default=EventType.RECOVERY, init=False)
    retry_count: int = 0
    max_retries: int = 0
    should_retry: bool = False
    reason: str = ""

    def _payload(self) -> dict[str, Any]:
        return {
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "should_retry": self.should_retry,
            "reason": self.reason,
        }


@dataclass(kw_only=True)
class LogEvent(Event):
    """General-purpose log message event."""

    type: EventType = field(default=EventType.LOG, init=False)
    level: str = "INFO"
    message: str = ""
    source: str = ""
    step_index: int | None = None

    def _payload(self) -> dict[str, Any]:
        return {"level": self.level, "message": self.message, "source": self.source, "step_index": self.step_index}


@dataclass(kw_only=True)
class ErrorEvent(Event):
    """Error event with structured details."""

    type: EventType = field(default=EventType.ERROR, init=False)
    error_type: str = ""
    message: str = ""
    recoverable: bool = False
    details: str | None = None

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error_type": self.error_type,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.details:
            payload["details"] = self.details[:1000]
        return payload