"""Load test cases from JSON files into domain objects."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.domain.test_case import TestCase, TestStep

_NAME_RE = re.compile(r"^TC-(\d+)-([PN]) :: (.+)$")


def load_from_json(file_path: str | Path) -> list[TestCase]:
    """Parse a JSON test-suite file and return domain :class:`TestCase` objects.

    Expected format::

        {
          "testcases": [
            {
              "name": "TC-001-P :: Login Test",
              "url": "https://example.com",
              "actions": [
                {"action": "Click login", "expectedResult": "Form visible"}
              ]
            }
          ]
        }

    Raises:
        FileNotFoundError: If *file_path* does not exist.
        ValueError: If a test-case name does not match ``TC-NNN-[PN] :: …``.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    cases: list[TestCase] = []

    for tc in data.get("testcases", []):
        match = _NAME_RE.match(tc["name"])
        if not match:
            raise ValueError(f"Invalid test case name format: {tc['name']}")

        steps = [
            TestStep(
                action=step.get("action", ""),
                assertion=step.get("assertion") or step.get("expectedResult", ""),
            )
            for step in tc.get("actions", [])
        ]

        cases.append(
            TestCase(
                id=match.group(1),
                type=match.group(2),
                name=match.group(3).strip(),
                url=tc["url"],
                steps=steps,
            )
        )

    return cases