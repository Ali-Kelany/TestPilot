"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ── Projects ────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
    test_cases_count: int = 0

    class Config:
        from_attributes = True


class ProjectStats(BaseModel):
    test_cases_count: int
    total_runs: int
    passed_runs: int
    failed_runs: int
    success_rate: float


# ── Test Steps ──────────────────────────────────────────────────


class TestStepSchema(BaseModel):
    """API-layer step representation (separate from domain TestStep)."""

    action: str
    assertion: str


# ── Test Cases ──────────────────────────────────────────────────


class TestCaseCreate(BaseModel):
    project_id: str
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(default="P", pattern="^[PN]$")
    target_url: str
    steps: list[TestStepSchema]
    external_id: str | None = None


class TestCaseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    type: str | None = Field(None, pattern="^[PN]$")
    target_url: str | None = None
    steps: list[TestStepSchema] | None = None


class TestCaseResponse(BaseModel):
    id: str
    project_id: str
    external_id: str | None
    name: str
    type: str
    target_url: str
    steps: list[TestStepSchema]
    created_at: datetime
    runs_count: int = 0
    last_run_status: str | None = None

    class Config:
        from_attributes = True


# ── Step Results ────────────────────────────────────────────────


class StepResultResponse(BaseModel):
    id: int
    step_number: int
    status: str
    retry_count: int
    result_reason: str | None
    screenshot_observation_id: int | None
    screenshot_verification_id: int | None
    executed_at: datetime

    class Config:
        from_attributes = True


# ── Test Runs ───────────────────────────────────────────────────


class TestRunCreate(BaseModel):
    provider: str = "google"
    model: str | None = None
    headless: bool = True


class TestRunResponse(BaseModel):
    id: str
    test_case_id: str
    project_id: str
    test_case_name: str
    status: str
    provider: str | None
    model: str | None
    duration_seconds: float | None
    steps_passed: int
    steps_failed: int
    total_tokens: int | None = None
    started_at: datetime
    completed_at: datetime | None
    step_results: list[StepResultResponse] = []
    steps: list[TestStepSchema] = []

    class Config:
        from_attributes = True


class TestRunListResponse(BaseModel):
    id: str
    test_case_id: str
    test_case_name: str
    status: str
    provider: str | None
    duration_seconds: float | None
    steps_passed: int
    steps_failed: int
    total_tokens: int | None = None
    started_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


# ── Errors ──────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None


# ── Pagination ──────────────────────────────────────────────────


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int
