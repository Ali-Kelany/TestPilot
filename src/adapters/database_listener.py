"""Database listener — persists execution events to SQLite.

Key improvements over the previous version:

- Screenshots are stored as BLOBs in the ``screenshots`` table via
  ``StepCompletedEvent.screenshot_observation/verification`` bytes.
- Log lines are stored as rows in ``run_log_entries`` via a new
  ``_on_log`` handler — no more reading files from disk.
- ``output_dir`` is gone from every call site.
- ``action`` / ``assertion`` are gone from ``create_step_result`` —
  they live in ``test_cases.steps_json``.
- Handler errors are **logged and swallowed** — they must never crash
  the execution or block other event handlers.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.domain.events import (
    ErrorEvent,
    EventType,
    ExecutionCompletedEvent,
    ExecutionStartedEvent,
    LogEvent,
    StepCompletedEvent,
)
from src.infrastructure.database import Database, Repository
from src.infrastructure.database import models as orm
from src.services.event_bus import EventBus

logger = logging.getLogger(__name__)


class DatabaseListener:
    """Subscribe to execution events and persist them to the database.

    Usage::

        bus = EventBus()
        db = Database("data/web_agent.db")
        listener = DatabaseListener(bus, db)
        listener.attach()

        result = await service.execute(test_case, config)

        listener.detach()
    """

    def __init__(self, event_bus: EventBus, database: Database) -> None:
        self._bus = event_bus
        self._db = database
        self._repo = Repository()
        self._unsubscribe_funcs: list = []
        self._current_run_id: str | None = None
        self._current_test_case_id: str | None = None

    # ── lifecycle ───────────────────────────────────────────────

    def attach(self) -> None:
        """Subscribe to events."""
        handlers = [
            (EventType.EXECUTION_STARTED, self._on_execution_started),
            (EventType.EXECUTION_COMPLETED, self._on_execution_completed),
            (EventType.STEP_COMPLETED, self._on_step_completed),
            (EventType.ERROR, self._on_error),
            (EventType.LOG, self._on_log),
        ]

        for event_type, handler in handlers:
            unsub = self._bus.subscribe(handler, event_type)
            self._unsubscribe_funcs.append(unsub)

    def detach(self) -> None:
        """Unsubscribe all handlers and reset state."""
        for unsub in self._unsubscribe_funcs:
            unsub()
        self._unsubscribe_funcs.clear()
        self._current_run_id = None
        self._current_test_case_id = None

    # ── event handlers ──────────────────────────────────────────
    #
    # Every handler is wrapped in try/except so that a persistence
    # failure never propagates to the EventBus or blocks other
    # handlers.

    async def _on_execution_started(
        self, event: ExecutionStartedEvent
    ) -> None:
        """Create a ``TestRun`` row for the new execution."""
        try:
            with self._db.session() as session:
                # Resolve or create the test case row
                test_case = self._resolve_test_case(session, event)
                self._current_test_case_id = test_case.id

                # Create the run (no output_dir)
                run = self._repo.create_test_run(
                    session,
                    run_id=event.session_id,
                    test_case_id=test_case.id,
                    status="running",
                    provider=event.provider,
                    model=event.model,
                )
                self._current_run_id = run.id

        except Exception:
            logger.error(
                "Failed to persist ExecutionStarted "
                "(session_id=%s)",
                event.session_id,
                exc_info=True,
            )

    async def _on_execution_completed(
        self, event: ExecutionCompletedEvent
    ) -> None:
        """Update the ``TestRun`` row with final status."""
        if not self._current_run_id:
            return

        try:
            with self._db.session() as session:
                self._repo.update_test_run(
                    session,
                    self._current_run_id,
                    status=event.result,
                    duration_seconds=event.duration_seconds,
                    steps_passed=event.steps_passed,
                    steps_failed=event.steps_failed,
                    total_tokens=event.total_tokens,
                    completed_at=datetime.now(timezone.utc),
                )


        except Exception:
            logger.error(
                "Failed to persist ExecutionCompleted "
                "(run_id=%s)",
                self._current_run_id,
                exc_info=True,
            )
        finally:
            self._current_run_id = None
            self._current_test_case_id = None

    async def _on_step_completed(
        self, event: StepCompletedEvent
    ) -> None:
        """Persist screenshot BLOBs then create a ``StepResult`` row."""
        if not self._current_run_id:
            return

        try:
            with self._db.session() as session:
                obs_id: int | None = None
                ver_id: int | None = None

                if event.screenshot_observation:
                    obs = orm.Screenshot(
                        test_run_id=self._current_run_id,
                        step_number=event.step_index,
                        kind="observation",
                        data=event.screenshot_observation,
                        mime_type="image/jpeg",
                    )
                    session.add(obs)
                    session.flush()
                    obs_id = obs.id

                if event.screenshot_verification:
                    ver = orm.Screenshot(
                        test_run_id=self._current_run_id,
                        step_number=event.step_index,
                        kind="verification",
                        data=event.screenshot_verification,
                        mime_type="image/jpeg",
                    )
                    session.add(ver)
                    session.flush()
                    ver_id = ver.id

                self._repo.create_step_result(
                    session,
                    test_run_id=self._current_run_id,
                    step_number=event.step_index,
                    status="passed" if event.passed else "failed",
                    retry_count=event.retry_count,
                    result_reason=event.reason,
                    screenshot_observation_id=obs_id,
                    screenshot_verification_id=ver_id,
                )

        except Exception:
            logger.error(
                "Failed to persist StepCompleted "
                "(run_id=%s, step=%d)",
                self._current_run_id,
                event.step_index,
                exc_info=True,
            )

    async def _on_error(self, event: ErrorEvent) -> None:
        """Mark the run as ``error`` if it is still ``running``."""
        if not self._current_run_id:
            return

        try:
            with self._db.session() as session:
                run = self._repo.get_test_run(
                    session, self._current_run_id
                )
                if run and run.status == "running":
                    self._repo.update_test_run(
                        session,
                        self._current_run_id,
                        status="error",
                        completed_at=datetime.now(timezone.utc),
                    )

        except Exception:
            logger.error(
                "Failed to persist Error event (run_id=%s)",
                self._current_run_id,
                exc_info=True,
            )

    async def _on_log(self, event: LogEvent) -> None:
        """Persist a log message as a ``RunLogEntry`` row."""
        if not self._current_run_id:
            return

        try:
            with self._db.session() as session:
                session.add(
                    orm.RunLogEntry(
                        test_run_id=self._current_run_id,
                        step_number=event.step_index,
                        level=event.level,
                        message=event.message,
                    )
                )

        except Exception:
            logger.error(
                "Failed to persist LogEvent (run_id=%s)",
                self._current_run_id,
                exc_info=True,
            )

    # ── private helpers ─────────────────────────────────────────

    def _resolve_test_case(
        self,
        session,
        event: ExecutionStartedEvent,
    ) -> orm.TestCase:
        """Find an existing ORM test case or create a placeholder.

        Lookup: exact match on ``external_id`` or ``id``.
        """
        tc: orm.TestCase | None = (
            session.query(orm.TestCase)
            .filter(
                (orm.TestCase.external_id == event.test_case_id)
                | (orm.TestCase.id == event.test_case_id)
            )
            .first()
        )

        if tc is not None:
            return tc

        # Auto-create project + test case if nothing matches
        project = session.query(orm.Project).first()
        if project is None:
            project = orm.Project(
                name="Default Project", description="Auto-created"
            )
            session.add(project)
            session.flush()

        tc = orm.TestCase(
            project_id=project.id,
            external_id=event.test_case_id,
            name=event.test_case_name,
            type="P",
            target_url=event.test_case_url,
            steps_json=getattr(event, "steps", []),
        )
        session.add(tc)
        session.flush()
        return tc