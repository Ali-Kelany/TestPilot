"""Converters between ORM models and domain objects.

These functions **must** be called inside an open session since they may
access lazy-loaded relationships.
"""

from __future__ import annotations

from src.domain.test_case import TestCase, TestStep
from src.infrastructure.database.models import TestCase as ORMTestCase


def orm_to_domain(orm_test_case: ORMTestCase) -> TestCase:
    """Convert an ORM ``TestCase`` row to a domain :class:`TestCase`.

    Must be called while the owning session is still open.
    """
    steps: list[TestStep] = []
    if orm_test_case.steps_json:
        for step in orm_test_case.steps_json:
            steps.append(
                TestStep(
                    action=step.get("action", ""),
                    assertion=step.get("assertion", "")
                    or step.get("expectedResult", ""),
                )
            )

    return TestCase(
        id=orm_test_case.id,
        name=orm_test_case.name,
        type=orm_test_case.type,
        url=orm_test_case.target_url,
        steps=steps,
    )


def domain_to_steps_json(test_case: TestCase) -> list[dict]:
    """Convert domain :class:`TestCase` steps to the JSON format used by
    :attr:`ORMTestCase.steps_json`."""
    return [
        {"action": step.action, "assertion": step.assertion}
        for step in test_case.steps
    ]
