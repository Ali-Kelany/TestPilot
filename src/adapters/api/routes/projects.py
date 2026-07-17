"""Project management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.adapters.api.dependencies import get_session
from src.adapters.api.routes.utils import (
    paginate,
    list_test_cases_for_project,
)
from src.adapters.api.schemas import (
    PaginationParams,
    PaginatedResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectStats,
    ProjectUpdate,
    TestRunListResponse,
)
from src.infrastructure.database.repository import Repository

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    session: Session = Depends(get_session),
):
    """Create a new project."""
    project = Repository.create_project(
        session, name=body.name, description=body.description
    )
    # Optimization: A new project has 0 test cases, no need to query.
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        test_cases_count=0,
    )


@router.get("", response_model=PaginatedResponse)
async def list_projects(
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
):
    """List all projects with pagination."""
    total = Repository.count_projects(session)
    offset = (pagination.page - 1) * pagination.page_size
    all_projects = Repository.get_projects_page(session, offset, pagination.page_size)
    counts = Repository.get_test_case_counts_by_project(session)
    result = []
    for p in all_projects:
        result.append(
            ProjectResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                created_at=p.created_at,
                test_cases_count=counts.get(p.id, 0),
            )
        )

    return paginate(total, result, pagination)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Get project details."""
    project = Repository.get_project(session, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    count = Repository.get_test_case_counts_by_project(session).get(project_id, 0)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        test_cases_count=count,
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    session: Session = Depends(get_session),
):
    """Update a project."""
    project = Repository.update_project(
        session, project_id, name=body.name, description=body.description
    )
    if not project:
        raise HTTPException(404, "Project not found")

    count = Repository.get_test_case_counts_by_project(session).get(project_id, 0)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        test_cases_count=count,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Delete a project."""
    if not Repository.delete_project(session, project_id):
        raise HTTPException(404, "Project not found")


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Get high-level stats for a project."""
    project = Repository.get_project(session, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    return Repository.get_project_stats(session, project_id)


@router.get("/{project_id}/test-cases", response_model=PaginatedResponse)
async def list_project_test_cases(
    project_id: str,
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
):
    """List all test cases in a project with pagination."""
    project = Repository.get_project(session, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    return list_test_cases_for_project(session, project_id, pagination)


@router.get("/{project_id}/test-runs", response_model=PaginatedResponse)
async def list_project_test_runs(
    project_id: str,
    pagination: PaginationParams = Depends(),
    session: Session = Depends(get_session),
):
    """List all test runs across all test cases in a project with pagination."""
    project = Repository.get_project(session, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    total = Repository.count_test_runs_by_project(session, project_id)
    offset = (pagination.page - 1) * pagination.page_size
    all_runs = Repository.get_test_runs_page_by_project(
        session, project_id, offset, pagination.page_size
    )

    items = [
        TestRunListResponse(
            id=run.id,
            test_case_id=run.test_case_id,
            test_case_name=run.test_case.name,
            status=run.status,
            provider=run.provider,
            duration_seconds=run.duration_seconds,
            steps_passed=run.steps_passed,
            steps_failed=run.steps_failed,
            total_tokens=run.total_tokens,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in all_runs
    ]

    return paginate(total, items, pagination)
