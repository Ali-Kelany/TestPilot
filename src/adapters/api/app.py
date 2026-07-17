"""FastAPI application with lifespan management.

Startup:  create Settings, Database, ExecutionManager; create tables.
Shutdown: cancel active executions, sweep orphaned runs, dispose engine.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import Settings
from src.infrastructure.database import Database
from src.infrastructure.database import models as orm
from src.adapters.api.execution_manager import ExecutionManager
from src.adapters.api.routes import projects, test_cases, test_runs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic."""

    # ── startup ─────────────────────────────────────────────────
    load_dotenv(find_dotenv())
    settings = Settings()

    db_path = settings.db_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    database = Database(db_path)
    database.create_tables()

    manager = ExecutionManager(database, settings)

    app.state.settings = settings
    app.state.database = database
    app.state.execution_manager = manager

    logger.info("Application started (db=%s)", db_path)

    yield

    # ── shutdown ────────────────────────────────────────────────
    await manager.cancel_all()
    database.dispose()

    logger.info("Application shut down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="Web Agent API",
        description="API for managing and executing web automation tests",
        version="1.0.0",
        lifespan=lifespan,
    )

    origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=origins != ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "1.0.0"}

    app.include_router(projects.router, prefix="/api")
    app.include_router(test_cases.router, prefix="/api")
    app.include_router(test_runs.router, prefix="/api")

    return app