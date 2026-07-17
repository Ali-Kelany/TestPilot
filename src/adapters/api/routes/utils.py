"""Shared utilities for route handlers."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.infrastructure.database.repository import Repository
from src.adapters.api.schemas import (
    TestStepSchema,
    TestCaseResponse,
    StepResultResponse,
    TestRunResponse,
    PaginationParams,
    PaginatedResponse,
)


def _json_to_steps(steps_json: list[dict]) -> list[TestStepSchema]:
    """Convert JSON steps from DB to API schema."""
    return [
        TestStepSchema(
            action=s["action"],
            assertion=s.get("assertion") or s.get("expectedResult", ""),
        )
        for s in steps_json
    ]


def _tc_response(tc, runs_count: int, last_run_status: str | None = None) -> TestCaseResponse:
    """Convert a TestCase DB model to a TestCaseResponse API schema."""
    return TestCaseResponse(
        id=tc.id,
        project_id=tc.project_id,
        external_id=tc.external_id,
        name=tc.name,
        type=tc.type,
        target_url=tc.target_url,
        steps=_json_to_steps(tc.steps_json),
        created_at=tc.created_at,
        runs_count=runs_count,
        last_run_status=last_run_status,
    )


def _step_result_response(sr) -> StepResultResponse:
    """Convert a StepResult DB model to a StepResultResponse API schema."""
    return StepResultResponse(
        id=sr.id,
        step_number=sr.step_number,
        status=sr.status,
        retry_count=sr.retry_count,
        result_reason=sr.result_reason,
        screenshot_observation_id=sr.screenshot_observation_id,
        screenshot_verification_id=sr.screenshot_verification_id,
        executed_at=sr.executed_at,
    )


def _run_response(run, test_case_name: str, project_id: str, steps, step_results=None) -> TestRunResponse:
    """Convert a TestRun DB model to a TestRunResponse API schema."""
    return TestRunResponse(
        id=run.id,
        test_case_id=run.test_case_id,
        project_id=project_id,
        test_case_name=test_case_name,
        status=run.status,
        provider=run.provider,
        model=run.model,
        duration_seconds=run.duration_seconds,
        steps_passed=run.steps_passed,
        steps_failed=run.steps_failed,
        total_tokens=run.total_tokens,
        started_at=run.started_at,
        completed_at=run.completed_at,
        steps=_json_to_steps(steps) if steps else [],
        step_results=[
            _step_result_response(sr) for sr in (step_results or [])
        ],
    )


def list_test_cases_for_project(
    session: Session,
    project_id: str,
    pagination: PaginationParams,
) -> PaginatedResponse:
    """Shared logic for listing test cases of a project."""
    total = Repository.count_test_cases_by_project(session, project_id)
    offset = (pagination.page - 1) * pagination.page_size
    test_cases = Repository.get_test_cases_page_by_project(
        session, project_id, offset, pagination.page_size
    )
    tc_ids = [tc.id for tc in test_cases]
    counts = Repository.get_run_counts_for_test_cases(session, tc_ids)
    last_statuses = Repository.get_last_run_statuses_for_test_cases(session, tc_ids)
    items = [
        _tc_response(tc, counts.get(tc.id, 0), last_statuses.get(tc.id))
        for tc in test_cases
    ]
    return paginate(total, items, pagination)


def paginate(total: int, items: list, params: PaginationParams) -> PaginatedResponse:
    """Generic pagination helper for list endpoints."""
    pages = (total + params.page_size - 1) // params.page_size
    return PaginatedResponse(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
        pages=pages,
    )
