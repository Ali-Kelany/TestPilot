"""Test run routes — history, screenshots, and logs.

Screenshots and logs are now served from the database (BLOBs and
``RunLogEntry`` rows) — no filesystem access required.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.adapters.api.dependencies import get_session
from src.adapters.api.routes.utils import _run_response
from src.adapters.api.schemas import (
    TestRunResponse,
)
from src.infrastructure.database import Repository

router = APIRouter(prefix="/test-runs", tags=["test-runs"])


@router.get("/{run_id}", response_model=TestRunResponse)
async def get_test_run(
    run_id: str,
    session: Session = Depends(get_session),
):
    """Get detailed information about a specific test run."""
    run = Repository.get_test_run(session, run_id)
    if not run:
        raise HTTPException(404, "Test run not found")

    tc = Repository.get_test_case(session, run.test_case_id)
    tc_name = tc.name if tc else "Unknown"
    steps = Repository.get_step_results_by_run(session, run.id)

    return _run_response(run, tc_name, tc.project_id, tc.steps_json, steps)


@router.delete("/{run_id}", status_code=204)
async def delete_test_run(
    run_id: str,
    session: Session = Depends(get_session),
):
    """Delete a test run and all associated data."""
    if not Repository.delete_test_run(session, run_id):
        raise HTTPException(404, "Test run not found")


# ── Screenshots ─────────────────────────────────────────────────


@router.get("/{run_id}/screenshots")
async def list_screenshots(
    run_id: str,
    session: Session = Depends(get_session),
):
    """List all screenshots for a test run (metadata only, no bytes)."""
    run = Repository.get_test_run(session, run_id)
    if not run:
        raise HTTPException(404, "Test run not found")

    screenshots = Repository.get_screenshots_by_run(session, run_id)
    return {
        "screenshots": [
            {
                "index": i + 1,
                "id": s.id,
                "step_number": s.step_number,
                "kind": s.kind,
                "sequence": s.sequence,
                "mime_type": s.mime_type,
                "captured_at": s.captured_at.isoformat(),
                "url": f"/api/test-runs/{run_id}/screenshots/{s.id}",
            }
            for i, s in enumerate(screenshots)
        ]
    }


@router.get("/{run_id}/screenshots/{screenshot_id}")
async def get_screenshot(
    run_id: str,
    screenshot_id: int,
    session: Session = Depends(get_session),
):
    """Get a specific screenshot by its unique ID. Ownership checked."""
    screenshot = Repository.get_screenshot_by_id(session, screenshot_id)
    if not screenshot or screenshot.test_run_id != run_id:
        raise HTTPException(404, "Screenshot not found for this run")
    return Response(content=screenshot.data, media_type=screenshot.mime_type)


# ── Logs ────────────────────────────────────────────────────────


@router.get("/{run_id}/logs")
async def get_logs(
    run_id: str,
    lines: int | None = None,
    session: Session = Depends(get_session),
):
    """Fetch execution log entries for a test run from the database.

    Args:
        run_id: The test run ID.
        lines: Optional number of most-recent lines to return.
    """
    run = Repository.get_test_run(session, run_id)
    if not run:
        raise HTTPException(404, "Test run not found")

    entries = Repository.get_log_entries_by_run(session, run_id)
    all_lines = [
        f"{e.logged_at.isoformat()} - {e.level} - {e.message}"
        for e in entries
    ]

    if lines and lines > 0:
        all_lines = all_lines[-lines:]

    return {"logs": "\n".join(all_lines)}
