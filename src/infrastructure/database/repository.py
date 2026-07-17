"""Stateless repository — every method takes a session as its first argument.

Usage::

    repo = Repository()

    with db.session() as session:
        project = repo.create_project(session, name="My Project")
        cases = repo.get_test_cases_by_project(session, project.id)
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.infrastructure.database.models import (
    Project,
    RunLogEntry,
    Screenshot,
    StepResult,
    TestCase,
    TestRun,
)


class Repository:
    """Data-access object.  Stateless — all state lives in the ``Session``."""

    @staticmethod
    def create_project(
        session: Session,
        name: str,
        description: str | None = None,
    ) -> Project:
        project = Project(name=name, description=description)
        session.add(project)
        session.flush()
        return project

    @staticmethod
    def get_project(session: Session, project_id: str) -> Project | None:
        return session.query(Project).filter_by(id=project_id).first()

    @staticmethod
    def count_projects(session: Session) -> int:
        return session.query(func.count(Project.id)).scalar()

    @staticmethod
    def get_projects_page(
        session: Session, offset: int, limit: int
    ) -> list[Project]:
        return (
            session.query(Project)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_all_projects(session: Session) -> list[Project]:
        return (
            session.query(Project)
            .order_by(Project.created_at.desc())
            .all()
        )

    @staticmethod
    def update_project(
        session: Session,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> Project | None:
        project = session.query(Project).filter_by(id=project_id).first()
        if project is None:
            return None
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        session.flush()
        return project

    @staticmethod
    def delete_project(session: Session, project_id: str) -> bool:
        project = session.query(Project).filter_by(id=project_id).first()
        if project is None:
            return False
        session.delete(project)
        session.flush()
        return True

    @staticmethod
    def create_test_case(
        session: Session,
        project_id: str,
        name: str,
        test_type: str,
        target_url: str,
        steps: list[dict],
        external_id: str | None = None,
    ) -> TestCase:
        test_case = TestCase(
            project_id=project_id,
            external_id=external_id,
            name=name,
            type=test_type,
            target_url=target_url,
            steps_json=steps,
        )
        session.add(test_case)
        session.flush()
        return test_case

    @staticmethod
    def get_test_case(
        session: Session, test_case_id: str
    ) -> TestCase | None:
        return session.query(TestCase).filter_by(id=test_case_id).first()

    @staticmethod
    def count_test_cases_by_project(
        session: Session, project_id: str
    ) -> int:
        return (
            session.query(func.count(TestCase.id))
            .filter_by(project_id=project_id)
            .scalar()
        )

    @staticmethod
    def get_test_cases_page_by_project(
        session: Session, project_id: str, offset: int, limit: int
    ) -> list[TestCase]:
        return (
            session.query(TestCase)
            .filter_by(project_id=project_id)
            .order_by(TestCase.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_test_cases_by_project(
        session: Session, project_id: str
    ) -> list[TestCase]:
        return (
            session.query(TestCase)
            .filter_by(project_id=project_id)
            .order_by(TestCase.created_at.desc())
            .all()
        )

    @staticmethod
    def update_test_case(
        session: Session, test_case_id: str, **kwargs
    ) -> TestCase | None:
        test_case = session.query(TestCase).filter_by(id=test_case_id).first()
        if test_case is None:
            return None
        for key, value in kwargs.items():
            if hasattr(test_case, key):
                setattr(test_case, key, value)
        session.flush()
        return test_case

    @staticmethod
    def delete_test_case(session: Session, test_case_id: str) -> bool:
        test_case = (
            session.query(TestCase).filter_by(id=test_case_id).first()
        )
        if test_case is None:
            return False
        session.delete(test_case)
        session.flush()
        return True

    @staticmethod
    def create_test_run(
        session: Session,
        run_id: str,
        test_case_id: str,
        status: str = "running",
        provider: str | None = None,
        model: str | None = None,
    ) -> TestRun:
        test_run = TestRun(
            id=run_id,
            test_case_id=test_case_id,
            status=status,
            provider=provider,
            model=model,
        )
        session.add(test_run)
        session.flush()
        return test_run

    @staticmethod
    def get_test_run(
        session: Session, test_run_id: str
    ) -> TestRun | None:
        return session.query(TestRun).filter_by(id=test_run_id).first()

    @staticmethod
    def count_test_runs_by_test_case(
        session: Session, test_case_id: str
    ) -> int:
        return (
            session.query(func.count(TestRun.id))
            .filter_by(test_case_id=test_case_id)
            .scalar()
        )

    @staticmethod
    def get_test_runs_page_by_test_case(
        session: Session, test_case_id: str, offset: int, limit: int
    ) -> list[TestRun]:
        return (
            session.query(TestRun)
            .filter_by(test_case_id=test_case_id)
            .options(joinedload(TestRun.test_case))
            .order_by(TestRun.started_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_test_runs_by_test_case(
        session: Session, test_case_id: str, limit: int = 50
    ) -> list[TestRun]:
        return (
            session.query(TestRun)
            .filter_by(test_case_id=test_case_id)
            .options(joinedload(TestRun.test_case))
            .order_by(TestRun.started_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_test_runs_by_project(
        session: Session, project_id: str
    ) -> int:
        return (
            session.query(func.count(TestRun.id))
            .join(TestRun.test_case)
            .filter(TestCase.project_id == project_id)
            .scalar()
        )

    @staticmethod
    def get_test_runs_page_by_project(
        session: Session, project_id: str, offset: int, limit: int
    ) -> list[TestRun]:
        return (
            session.query(TestRun)
            .join(TestRun.test_case)
            .filter(TestCase.project_id == project_id)
            .options(joinedload(TestRun.test_case))
            .order_by(TestRun.started_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_test_runs_by_project(
        session: Session, project_id: str
    ) -> list[TestRun]:
        """Fetch all test runs for a project by joining through TestCase."""
        return (
            session.query(TestRun)
            .join(TestRun.test_case)
            .filter(TestCase.project_id == project_id)
            .options(joinedload(TestRun.test_case))
            .order_by(TestRun.started_at.desc())
            .all()
        )

    @staticmethod
    def update_test_run(
        session: Session,
        test_run_id: str,
        **kwargs,
    ) -> TestRun | None:
        test_run = session.query(TestRun).filter_by(id=test_run_id).first()
        if test_run is None:
            return None
        for key, value in kwargs.items():
            if hasattr(test_run, key):
                setattr(test_run, key, value)
        session.flush()
        return test_run

    @staticmethod
    def delete_test_run(session: Session, test_run_id: str) -> bool:
        test_run = session.query(TestRun).filter_by(id=test_run_id).first()
        if test_run is None:
            return False
        session.delete(test_run)
        session.flush()
        return True

    @staticmethod
    def create_step_result(
        session: Session,
        test_run_id: str,
        step_number: int,
        status: str,
        retry_count: int = 0,
        result_reason: str | None = None,
        screenshot_observation_id: int | None = None,
        screenshot_verification_id: int | None = None,
    ) -> StepResult:
        step_result = StepResult(
            test_run_id=test_run_id,
            step_number=step_number,
            status=status,
            retry_count=retry_count,
            result_reason=result_reason,
            screenshot_observation_id=screenshot_observation_id,
            screenshot_verification_id=screenshot_verification_id,
        )
        session.add(step_result)
        session.flush()
        return step_result

    @staticmethod
    def get_step_results_by_run(
        session: Session, test_run_id: str
    ) -> list[StepResult]:
        return (
            session.query(StepResult)
            .filter_by(test_run_id=test_run_id)
            .order_by(StepResult.step_number)
            .all()
        )

    @staticmethod
    def get_screenshots_by_run(
        session: Session, test_run_id: str
    ) -> list[Screenshot]:
        """Return all screenshots for a run ordered by step, kind, sequence."""
        return (
            session.query(Screenshot)
            .filter_by(test_run_id=test_run_id)
            .order_by(
                Screenshot.step_number,
                Screenshot.kind,
                Screenshot.sequence,
            )
            .all()
        )

    @staticmethod
    def get_screenshot_by_id(
        session: Session, screenshot_id: int
    ) -> Screenshot | None:
        return session.query(Screenshot).filter_by(id=screenshot_id).first()

    @staticmethod
    def get_log_entries_by_run(
        session: Session, test_run_id: str
    ) -> list[RunLogEntry]:
        """Return all log entries for a run ordered by timestamp."""
        return (
            session.query(RunLogEntry)
            .filter_by(test_run_id=test_run_id)
            .order_by(RunLogEntry.logged_at)
            .all()
        )

    @staticmethod
    def get_test_case_counts_by_project(session: Session) -> dict[str, int]:
        """Return a mapping of project_id -> test_case_count for all projects."""
        rows = (
            session.query(Project.id, func.count(TestCase.id))
            .outerjoin(TestCase)
            .group_by(Project.id)
            .all()
        )
        return {pid: count for pid, count in rows}

    @staticmethod
    def get_run_counts_by_test_case(
        session: Session, project_id: str
    ) -> dict[str, int]:
        """Return a mapping of test_case_id -> run_count for all cases in a project."""
        rows = (
            session.query(TestCase.id, func.count(TestRun.id))
            .outerjoin(TestRun)
            .filter(TestCase.project_id == project_id)
            .group_by(TestCase.id)
            .all()
        )
        return {tc_id: count for tc_id, count in rows}

    @staticmethod
    def get_run_counts_for_test_cases(
        session: Session, test_case_ids: list[str]
    ) -> dict[str, int]:
        """Return a mapping of test_case_id -> run_count for specific test cases."""
        if not test_case_ids:
            return {}
        rows = (
            session.query(TestCase.id, func.count(TestRun.id))
            .outerjoin(TestRun)
            .filter(TestCase.id.in_(test_case_ids))
            .group_by(TestCase.id)
            .all()
        )
        return {tc_id: count for tc_id, count in rows}

    @staticmethod
    def get_run_count_for_test_case(
        session: Session, test_case_id: str
    ) -> int:
        return (
            session.query(func.count(TestRun.id))
            .filter_by(test_case_id=test_case_id)
            .scalar()
        )

    @staticmethod
    def get_last_run_statuses_for_test_cases(
        session: Session, test_case_ids: list[str]
    ) -> dict[str, str | None]:
        """Return a mapping of test_case_id -> last_run_status for specific test cases."""
        if not test_case_ids:
            return {}
        runs = (
            session.query(TestRun.test_case_id, TestRun.status)
            .filter(TestRun.test_case_id.in_(test_case_ids))
            .order_by(TestRun.started_at.asc())
            .all()
        )
        return {r.test_case_id: r.status for r in runs}

    @staticmethod
    def get_last_run_status_for_test_case(
        session: Session, test_case_id: str
    ) -> str | None:
        """Return the status of the latest run for a test case."""
        statuses = Repository.get_last_run_statuses_for_test_cases(session, [test_case_id])
        return statuses.get(test_case_id)

    @staticmethod
    def get_project_stats(session: Session, project_id: str):
        test_cases_count = (
            session.query(TestCase)
            .filter_by(project_id=project_id)
            .count()
        )

        test_case_ids = [
            tc.id
            for tc in session.query(TestCase.id)
            .filter_by(project_id=project_id)
            .all()
        ]

        runs_count = 0
        passed_count = 0
        failed_count = 0

        if test_case_ids:
            runs = (
                session.query(TestRun)
                .filter(TestRun.test_case_id.in_(test_case_ids))
                .all()
            )
            runs_count = len(runs)
            passed_count = sum(1 for r in runs if r.status == "passed")
            failed_count = sum(
                1 for r in runs if r.status in ("failed", "error")
            )

        terminal_runs_count = passed_count + failed_count
        success_rate = (passed_count / terminal_runs_count * 100) if terminal_runs_count > 0 else 0.0

        from src.adapters.api.schemas import ProjectStats

        return ProjectStats(
            test_cases_count=test_cases_count,
            total_runs=runs_count,
            passed_runs=passed_count,
            failed_runs=failed_count,
            success_rate=success_rate,
        )