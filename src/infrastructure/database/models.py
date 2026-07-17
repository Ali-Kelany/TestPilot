"""SQLAlchemy ORM models.

Import this module with a namespace alias::

    from src.infrastructure.database import models as orm
    orm.TestCase   # the ORM model
    orm.Project    # etc.

This avoids any collision with the domain ``TestCase`` dataclass.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Project(Base):
    """A project that groups test cases."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    test_cases: Mapped[list[TestCase]] = relationship(
        "TestCase", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id!r}, name={self.name!r})>"


class TestCase(Base):
    """A test case with steps, stored as JSON."""

    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(1), nullable=False)  # P or N
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    steps_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    project: Mapped[Project] = relationship("Project", back_populates="test_cases")
    test_runs: Mapped[list[TestRun]] = relationship(
        "TestRun", back_populates="test_case", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestCase(id={self.id!r}, name={self.name!r})>"


class TestRun(Base):
    """An execution of a test case."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    test_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_cases.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    steps_passed: Mapped[int] = mapped_column(Integer, default=0)
    steps_failed: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    test_case: Mapped[TestCase] = relationship(
        "TestCase", back_populates="test_runs"
    )
    step_results: Mapped[list[StepResult]] = relationship(
        "StepResult", back_populates="test_run", cascade="all, delete-orphan"
    )
    screenshots: Mapped[list[Screenshot]] = relationship(
        "Screenshot", back_populates="test_run", cascade="all, delete-orphan"
    )
    run_log_entries: Mapped[list[RunLogEntry]] = relationship(
        "RunLogEntry", back_populates="test_run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestRun(id={self.id!r}, status={self.status!r})>"


class Screenshot(Base):
    """A screenshot captured during a test run, stored as a BLOB.

    ``kind`` is either ``'observation'`` (before the action) or
    ``'verification'`` (after the action, used for assertion).
    ``sequence`` orders multiple observations within the same step.
    """

    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id"), nullable=False
    )
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # 'observation' | 'verification'
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(20), default="image/jpeg")
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    test_run: Mapped[TestRun] = relationship("TestRun", back_populates="screenshots")

    def __repr__(self) -> str:
        return (
            f"<Screenshot(id={self.id!r}, run={self.test_run_id!r}, "
            f"step={self.step_number}, kind={self.kind!r})>"
        )


class StepResult(Base):
    """Result of a single step execution.

    ``action`` and ``assertion`` are intentionally absent — derive them
    from ``test_case.steps_json[step_number - 1]`` to avoid duplication.
    Screenshot references are FK columns pointing to the ``screenshots``
    table rather than orphaned boolean flags.
    """

    __tablename__ = "step_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    result_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_observation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("screenshots.id"), nullable=True
    )
    screenshot_verification_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("screenshots.id"), nullable=True
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    test_run: Mapped[TestRun] = relationship(
        "TestRun", back_populates="step_results"
    )
    screenshot_observation: Mapped[Screenshot | None] = relationship(
        "Screenshot", foreign_keys=[screenshot_observation_id]
    )
    screenshot_verification: Mapped[Screenshot | None] = relationship(
        "Screenshot", foreign_keys=[screenshot_verification_id]
    )

    def __repr__(self) -> str:
        return (
            f"<StepResult(id={self.id!r}, step={self.step_number}, "
            f"status={self.status!r})>"
        )


class RunLogEntry(Base):
    """A single structured log line for a test run.

    ``step_number`` is nullable for run-level log messages not tied to a
    specific step.  The ``/logs`` API route queries this table instead of
    reading a file from disk.
    """

    __tablename__ = "run_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id"), nullable=False
    )
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(10), default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    logged_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    test_run: Mapped[TestRun] = relationship(
        "TestRun", back_populates="run_log_entries"
    )

    def __repr__(self) -> str:
        return (
            f"<RunLogEntry(id={self.id!r}, run={self.test_run_id!r}, "
            f"level={self.level!r})>"
        )
