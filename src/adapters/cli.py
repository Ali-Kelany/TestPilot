"""CLI adapter — formats execution events for terminal output.

Subscribes exclusively via ``EventBus.subscribe()`` (returns an
unsubscribe callable) to avoid handler leaks.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from typing import TextIO

from src.domain.events import (
    ErrorEvent,
    EventType,
    ExecutionCompletedEvent,
    ExecutionStartedEvent,
    LogEvent,
    ObservationEvent,
    RecoveryEvent,
    StepCompletedEvent,
    StepStartedEvent,
    ToolCalledEvent,
    ToolResultEvent,
    VerificationEvent,
)
from src.services.event_bus import EventBus


class CLIAdapter:
    """Render execution events as coloured terminal output.

    Usage::

        bus = EventBus()
        cli = CLIAdapter(bus)
        cli.attach()

        result = await service.execute(test_case, config)

        cli.detach()   # always clean up
    """

    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
    }

    def __init__(
        self,
        event_bus: EventBus,
        output: TextIO = sys.stdout,
        use_colors: bool = True,
        verbose: bool = False,
    ) -> None:
        self._bus = event_bus
        self._output = output
        self._use_colors = (
            use_colors and hasattr(output, "isatty") and output.isatty()
        )
        self._verbose = verbose
        self._start_time: float | None = None
        self._unsubscribe_funcs: list = []

    # ── lifecycle ───────────────────────────────────────────────

    def attach(self) -> None:
        """Subscribe to execution events."""
        handlers = [
            (EventType.EXECUTION_STARTED, self._on_execution_started),
            (EventType.EXECUTION_COMPLETED, self._on_execution_completed),
            (EventType.STEP_STARTED, self._on_step_started),
            (EventType.STEP_COMPLETED, self._on_step_completed),
            (EventType.TOOL_CALLED, self._on_tool_called),
            (EventType.TOOL_RESULT, self._on_tool_result),
            (EventType.VERIFICATION, self._on_verification),
            (EventType.RECOVERY, self._on_recovery),
            (EventType.OBSERVATION, self._on_observation),
            (EventType.ERROR, self._on_error),
        ]

        if self._verbose:
            handlers.append((EventType.LOG, self._on_log))

        for event_type, handler in handlers:
            unsub = self._bus.subscribe(handler, event_type)
            self._unsubscribe_funcs.append(unsub)

    def detach(self) -> None:
        """Unsubscribe all handlers."""
        for unsub in self._unsubscribe_funcs:
            unsub()
        self._unsubscribe_funcs.clear()

    # ── formatting helpers ──────────────────────────────────────

    def _color(self, text: str, *colors: str) -> str:
        if not self._use_colors:
            return text
        codes = "".join(self.COLORS.get(c, "") for c in colors)
        return f"{codes}{text}{self.COLORS['reset']}"

    def _elapsed(self) -> str:
        if self._start_time is None:
            return "00:00:00"
        elapsed = int(datetime.now(timezone.utc).timestamp() - self._start_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _write(self, text: str, newline: bool = True) -> None:
        self._output.write(text)
        if newline:
            self._output.write("\n")
        self._output.flush()

    def _header(self, text: str) -> None:
        line = "─" * 60
        self._write(f"\n{self._color(line, 'dim')}")
        self._write(f"{self._color(text, 'bold', 'cyan')}")
        self._write(f"{self._color(line, 'dim')}")

    # ── event handlers ──────────────────────────────────────────

    async def _on_execution_started(
        self, event: ExecutionStartedEvent
    ) -> None:
        self._start_time = event.timestamp.timestamp()

        self._header("EXECUTION STARTED")
        self._write(
            f"  Test Case: {self._color(event.test_case_name, 'bold')}"
        )
        self._write(f"  URL: {self._color(event.test_case_url, 'blue')}")
        self._write(f"  Steps: {event.total_steps}")
        self._write(f"  Provider: {event.provider} / {event.model}")
        self._write("")

    async def _on_execution_completed(
        self, event: ExecutionCompletedEvent
    ) -> None:
        result_color = "green" if event.result == "passed" else "red"

        self._header("EXECUTION COMPLETED")
        self._write(
            f"  Result: "
            f"{self._color(event.result.upper(), 'bold', result_color)}"
        )
        self._write(f"  Duration: {event.duration_seconds:.1f}s")
        self._write(
            f"  Steps: {event.steps_passed} passed, "
            f"{event.steps_failed} failed"
        )

        if event.final_log:
            self._write("\n  Log Summary:")
            for entry in event.final_log[-10:]:
                prefix = "    "
                if "PASSED" in entry:
                    self._write(
                        f"{prefix}{self._color('✓', 'green')} {entry}"
                    )
                elif "FAILED" in entry:
                    self._write(
                        f"{prefix}{self._color('✗', 'red')} {entry}"
                    )
                else:
                    self._write(f"{prefix}  {entry}")

        self._write("")

    async def _on_step_started(self, event: StepStartedEvent) -> None:
        step_info = f"Step {event.step_index}/{event.total_steps}"
        self._write(
            f"\n{self._color('[' + self._elapsed() + ']', 'dim')} "
            f"{self._color(step_info, 'bold', 'magenta')}"
        )
        self._write(f"  Action: {event.action}")
        self._write(f"  Assert: {event.assertion}")

    async def _on_step_completed(self, event: StepCompletedEvent) -> None:
        if event.passed:
            status = self._color("✓ PASSED", "bold", "green")
        else:
            status = self._color("✗ FAILED", "bold", "red")

        self._write(f"  Result: {status}")
        if event.reason:
            self._write(f"  Reason: {event.reason[:100]}")
        if event.retry_count > 0:
            self._write(f"  Retries: {event.retry_count}")

    async def _on_tool_called(self, event: ToolCalledEvent) -> None:
        args_str = ", ".join(
            f"{k}={v!r}" for k, v in event.tool_args.items()
        )
        self._write(
            f"  {self._color('→', 'yellow')} "
            f"{self._color(event.tool_name, 'cyan')}({args_str})"
        )

    async def _on_tool_result(self, event: ToolResultEvent) -> None:
        if event.success:
            indicator = self._color("←", "green")
            result = event.result[:80]
        else:
            indicator = self._color("←", "red")
            result = self._color(event.result[:80], "red")

        self._write(f"  {indicator} {result}")

    async def _on_verification(self, event: VerificationEvent) -> None:
        if event.passed:
            status = self._color("VERIFIED", "green")
        else:
            status = self._color("NOT VERIFIED", "red")

        if self._verbose:
            self._write(f"  Verification: {status}")
            self._write(f"    {event.reason[:100]}")

    async def _on_recovery(self, event: RecoveryEvent) -> None:
        if event.should_retry:
            self._write(
                f"  {self._color('↻', 'yellow')} "
                f"Retrying ({event.retry_count}/{event.max_retries}): "
                f"{event.reason}"
            )
        else:
            self._write(
                f"  {self._color('✗', 'red')} "
                f"Recovery abandoned: {event.reason}"
            )

    async def _on_observation(self, event: ObservationEvent) -> None:
        if self._verbose:
            self._write(
                f"  {self._color('👁', 'dim')} "
                f"Observed: {event.page_url[:50]} "
                f"({event.element_count} elements)"
            )

    async def _on_error(self, event: ErrorEvent) -> None:
        self._write(
            f"\n{self._color('ERROR:', 'bold', 'red')} "
            f"{event.error_type}: {event.message}"
        )
        if event.details:
            self._write(f"  Details: {event.details[:200]}")

    async def _on_log(self, event: LogEvent) -> None:
        level_colors = {
            "INFO": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
            "DEBUG": "dim",
        }
        color = level_colors.get(event.level, "dim")
        self._write(
            f"  {self._color('[' + event.level + ']', color)} "
            f"{event.message}"
        )