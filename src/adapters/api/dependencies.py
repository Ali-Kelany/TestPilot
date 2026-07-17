"""FastAPI dependency providers.

Every shared resource is accessed via ``Depends()`` — no module-level
mutable state in route files.
"""

from __future__ import annotations

from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.config import Settings
from src.infrastructure.database import Database
from src.adapters.api.execution_manager import ExecutionManager


def get_settings(request: Request) -> Settings:
    """Application-scoped settings singleton."""
    return request.app.state.settings


def get_database(request: Request) -> Database:
    """Application-scoped database singleton."""
    return request.app.state.database


def get_execution_manager(request: Request) -> ExecutionManager:
    """Application-scoped execution manager."""
    return request.app.state.execution_manager


def get_session(
    database: Database = Depends(get_database),
) -> Generator[Session, None, None]:
    """Request-scoped database session.

    Commits on success, rolls back on error, always closes.
    """
    with database.session() as session:
        yield session