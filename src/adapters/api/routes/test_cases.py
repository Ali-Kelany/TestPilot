"""Test case CRUD and execution routes."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session

from src.adapters.api.dependencies import (
    get_database,
    get_execution_manager,
    get_session,
)
from src.adapters.api.routes.utils import (
    _tc_response,
    _run_response,
    paginate,
    list_test_cases_for_project,
)
from src.adapters.api.schemas import (
    PaginationParams,
    PaginatedResponse,
    TestCaseCreate,
    TestCaseResponse,
    TestCaseUpdate,
    TestRunCreate,
    TestRunListResponse,
    TestRunResponse,
    TestStepSchema,
)
from src.adapters.api.execution_manager import ExecutionManager
from src.config import ExecutionConfig
from src.infrastructure.database import Database, Repository

router = APIRouter(prefix="/test-cases", tags=["test-cases"])
logger = logging.getLogger(__name__)


def _steps_to_json(steps: list[TestStepSchema]) -> list[dict]:
    """Convert API steps to JSON for storage."""
    return [{"action": s.action, "assertion": s.assertion} for s in steps]


@router.post("", response_model=TestCaseResponse, status_code=201)
async def create_test_case(
    body: TestCaseCreate,
    session: Session = Depends(get_session),
):
    """Create a new test case."""
    if not Repository.get_project(session, body.project_id):
        raise HTTPException(404, "Project not found")

    tc = Repository.create_test_case(
        session,
        project_id=body.project_id,
        name=body.name,
        test_type=body.type,
        target_url=body.target_url,
        steps=_steps_to_json(body.steps),
        external_id=body.external_id,
    )
    # A new test case has 0 runs.
    return _tc_response(tc, 0)


@router.get("", response_model=PaginatedResponse)
async def list_test_cases(
    project_id: str,
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
):
    """List all test cases for a project with pagination."""
    if not Repository.get_project(session, project_id):
        raise HTTPException(404, "Project not found")

    return list_test_cases_for_project(session, project_id, pagination)


@router.get("/{test_case_id}", response_model=TestCaseResponse)
async def get_test_case(
    test_case_id: str,
    session: Session = Depends(get_session),
):
    """Get test case details."""
    tc = Repository.get_test_case(session, test_case_id)
    if not tc:
        raise HTTPException(404, "Test case not found")

    count = Repository.get_run_count_for_test_case(session, tc.id)
    last_status = Repository.get_last_run_status_for_test_case(session, tc.id)
    return _tc_response(tc, count, last_status)


@router.put("/{test_case_id}", response_model=TestCaseResponse)
async def update_test_case(
    test_case_id: str,
    body: TestCaseUpdate,
    session: Session = Depends(get_session),
):
    """Update a test case."""
    update_data: dict = {}
    if body.name is not None:
        update_data["name"] = body.name
    if body.type is not None:
        update_data["type"] = body.type
    if body.target_url is not None:
        update_data["target_url"] = body.target_url
    if body.steps is not None:
        update_data["steps_json"] = _steps_to_json(body.steps)

    tc = Repository.update_test_case(session, test_case_id, **update_data)
    if not tc:
        raise HTTPException(404, "Test case not found")

    count = Repository.get_run_count_for_test_case(session, tc.id)
    last_status = Repository.get_last_run_status_for_test_case(session, tc.id)
    return _tc_response(tc, count, last_status)


@router.delete("/{test_case_id}", status_code=204)
async def delete_test_case(
    test_case_id: str,
    session: Session = Depends(get_session),
):
    """Delete a test case."""
    if not Repository.delete_test_case(session, test_case_id):
        raise HTTPException(404, "Test case not found")


# ── Execution ────────────────────────────────────────────────────


@router.post(
    "/{test_case_id}/run",
    response_model=TestRunResponse,
)
async def run_test_case(
    test_case_id: str,
    body: TestRunCreate,
    manager: ExecutionManager = Depends(get_execution_manager),
    database: Database = Depends(get_database),
):
    """Execute a test case synchronously and return the result."""
    config = ExecutionConfig(
        provider=body.provider,
        model=body.model,
        headless=body.headless,
    )

    try:
        handle = await manager.start(test_case_id, config)
    except ValueError as exc:
        raise HTTPException(404, str(exc))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))

    try:
        result = await handle.task
    except Exception as exc:
        raise HTTPException(500, f"Execution failed: {exc}")

    # Fetch persisted data
    with database.session() as session:
        run = Repository.get_test_run(session, result.session_id)
        if not run:
            raise HTTPException(500, "Test run not persisted")

        tc = Repository.get_test_case(session, run.test_case_id)
        tc_name = tc.name if tc else "Unknown"
        tc_steps = tc.steps_json if tc else []
        steps = Repository.get_step_results_by_run(session, run.id)

        return _run_response(run, tc_name, tc.project_id, tc_steps, steps)


@router.post("/{test_case_id}/stop")
async def stop_test_case(
    test_case_id: str,
    manager: ExecutionManager = Depends(get_execution_manager),
):
    """Stop a running test case execution."""
    cancelled = await manager.cancel(test_case_id)
    if not cancelled:
        raise HTTPException(409, "Test case is not running")
    return {"status": "stopped"}


# ── Test Runs for Test Case ──────────────────────────────────────


@router.get(
    "/{test_case_id}/runs",
    response_model=PaginatedResponse,
)
async def list_test_runs(
    test_case_id: str,
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
):
    """List test runs for a specific test case with pagination."""
    if not Repository.get_test_case(session, test_case_id):
        raise HTTPException(404, "Test case not found")

    total = Repository.count_test_runs_by_test_case(session, test_case_id)
    offset = (pagination.page - 1) * pagination.page_size
    all_runs = Repository.get_test_runs_page_by_test_case(
        session, test_case_id, offset, pagination.page_size
    )

    items = [
        TestRunListResponse(
            id=r.id,
            test_case_id=r.test_case_id,
            test_case_name=r.test_case.name,
            status=r.status,
            provider=r.provider,
            duration_seconds=r.duration_seconds,
            steps_passed=r.steps_passed,
            steps_failed=r.steps_failed,
            total_tokens=r.total_tokens,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in all_runs
    ]

    return paginate(total, items, pagination)


# ── WebSocket ────────────────────────────────────────────────────


@router.websocket("/{test_case_id}/execute")
async def websocket_execution(
    websocket: WebSocket,
    test_case_id: str,
):
    """Stream execution events over a WebSocket.

    1. Accept the connection.
    2. Optionally receive a JSON config message (1 s timeout).
    3. Start execution — events are forwarded as JSON frames.
    4. On completion or disconnect, unsubscribe and close cleanly.
    """
    await websocket.accept()

    manager = websocket.app.state.execution_manager

    # ── optional config from client ─────────────────────────────
    config = ExecutionConfig(headless=True)
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
        data = json.loads(raw)
        config = ExecutionConfig(
            provider=data.get("provider", "google"),
            model=data.get("model"),
            headless=data.get("headless", True),
        )
    except (asyncio.TimeoutError, json.JSONDecodeError):
        pass  # use defaults

    # ── start execution ─────────────────────────────────────────
    try:
        handle = await manager.start(test_case_id, config)
    except ValueError:
        await websocket.send_json({"type": "error", "message": "Test case not found"})
        await websocket.close(code=4004, reason="Test case not found")
        return
    except RuntimeError:
        await websocket.send_json({"type": "error", "message": "Already running"})
        await websocket.close(code=4009, reason="Already running")
        return

    # ── forward events ──────────────────────────────────────────
    client_disconnected = asyncio.Event()

    async def forward(event):
        if client_disconnected.is_set():
            return
        try:
            await websocket.send_json(event.to_dict())
        except Exception:
            client_disconnected.set()

    unsub = handle.event_bus.subscribe(forward)

    async def watch_disconnect():
        try:
            while not client_disconnected.is_set():
                await websocket.receive_text()
        except Exception:
            client_disconnected.set()

    try:
        done, pending = await asyncio.wait(
            [handle.task, asyncio.create_task(watch_disconnect())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        if handle.task in done and handle.task.exception() is None:
            result = handle.task.result()
            if not client_disconnected.is_set():
                await websocket.send_json({
                    "type": "done",
                    "result": result.result,
                    "session_id": result.session_id,
                })
    except asyncio.CancelledError:
        await websocket.send_json({
            "type": "error", "message": "Execution cancelled"
        })
    except Exception as exc:
        try:
            await websocket.send_json({
                "type": "error", "message": str(exc)
            })
        except Exception:
            logger.warning("Failed to send error frame", exc_info=True)
    finally:
        unsub()
        try:
            await websocket.close()
        except Exception:
            logger.warning("Failed to close WebSocket", exc_info=True)
