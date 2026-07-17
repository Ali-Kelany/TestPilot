from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Literal, TypedDict

from langchain.messages import AnyMessage
from langgraph.graph import add_messages

from src.domain.test_case import TestCase


class AgentState(TypedDict):
    """Represents the current state of the agent."""

    messages: Annotated[List[AnyMessage], add_messages]

    test_case: TestCase
    step_index: int
    step_action: str
    step_assertion: str

    loop_count: int
    retry_count: int

    page_url: str
    page_title: str
    screenshot: bytes | None

    memory: Annotated[Dict[str, Any], operator.ior]
    log: Annotated[list[str], operator.add]

    step_history: Annotated[list[dict], operator.add]

    result: Literal["running", "passed", "failed"]

    step_start_time: float


def create_initial_state(test_case: TestCase) -> AgentState:
    """Create the initial state for a test run."""
    return AgentState(
        messages=[],
        test_case=test_case,
        step_index=1,
        step_action="",
        step_assertion="",
        loop_count=0,
        retry_count=0,
        page_url="",
        page_title="",
        screenshot=None,
        memory={},
        log=[],
        step_history=[],
        result="running",
        step_start_time=0.0,
    )
