"""Domain objects for test specifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class TestStep:
    """A single action + expected-result pair."""

    __test__ = False

    action: str
    assertion: str


@dataclass
class TestCase:
    """An ordered sequence of test steps against a target URL."""

    __test__ = False

    id: str
    name: str
    type: str  # "P" (positive) or "N" (negative)
    url: str
    steps: list[TestStep]

    def get_step(self, n: int) -> TestStep:
        """Return step *n* (1-based).  Raises ``IndexError`` if out of range."""
        if not 1 <= n <= len(self.steps):
            raise IndexError(f"Step {n} out of range (1-{len(self.steps)})")
        return self.steps[n - 1]

    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self) -> Iterator[TestStep]:
        return iter(self.steps)

    def __str__(self) -> str:
        lines = [f"TC-{self.id}-{self.type}: {self.name}"]
        for idx, step in enumerate(self.steps, 1):
            lines.append(f"  {idx}. {step.action}")
            if step.assertion:
                lines.append(f"     Expected: {step.assertion}")
        return "\n".join(lines)