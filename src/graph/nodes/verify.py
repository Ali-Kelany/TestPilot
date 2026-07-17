from __future__ import annotations

import asyncio
import base64
import time
from typing import Literal

from langchain.messages import HumanMessage, SystemMessage
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.domain.events import StepCompletedEvent, VerificationEvent
from src.infrastructure.llm.prompts import ASSERTOR_SYSTEM, format_assertion_prompt
from src.graph.nodes.context import NodeContext
from src.graph.state import AgentState


class AssertionResult(BaseModel):
    """Structured output from the assertor model."""

    passed: bool = Field(description="Whether the assertion is satisfied.")
    reason: str = Field(description="Explanation of the verdict.")


class VerifyNode:
    """Take a clean screenshot, invoke the assertor model, and route to the next step (pass) or recovery (fail)."""

    def __init__(self, ctx: NodeContext) -> None:
        self._ctx = ctx

    async def __call__(
        self, state: AgentState
    ) -> Command[Literal["init_step", "recover"]]:
        ctx = self._ctx
        ctx.logger.info("Step %d: Verifying: %s", state["step_index"], state["step_assertion"])

        await ctx.browser.unmark_page()
        await asyncio.sleep(0.5)
        screenshot = await ctx.browser.screenshot()

        prompt_text = format_assertion_prompt(
            assertion=state["step_assertion"],
            action=state["step_action"],
            memory=state.get("memory", {}),
            step_history=state.get("step_history", []),
        )
        b64 = base64.b64encode(screenshot).decode()
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ]
        )

        try:
            verdict: AssertionResult = await ctx.assertor_model.ainvoke(
                [SystemMessage(content=ASSERTOR_SYSTEM), message]
            )
        except Exception as e:
            ctx.logger.error("Step %d: Assertion error: %s", state["step_index"], e)
            verdict = AssertionResult(passed=False, reason=str(e))

        idx = state["step_index"]
        duration = time.time() - state["step_start_time"]

        await ctx.emit(
            VerificationEvent(
                session_id=ctx.session_id,
                assertion=state["step_assertion"],
                passed=verdict.passed,
                reason=verdict.reason,
                duration_seconds=duration,
            )
        )

        if verdict.passed:
            ctx.logger.info("Step %d passed: %s", idx, verdict.reason)

            await ctx.emit(
                StepCompletedEvent(
                    session_id=ctx.session_id,
                    step_index=idx,
                    passed=True,
                    reason=verdict.reason,
                    duration_seconds=duration,
                    retry_count=state["retry_count"],
                    screenshot_observation=state.get("screenshot"),
                    screenshot_verification=screenshot,
                )
            )

            history_entry = {
                "step": idx,
                "url": state.get("page_url", ""),
                "title": state.get("page_title", ""),
                "action": state["step_action"],
                "assertion": state["step_assertion"],
                "outcome": verdict.reason,
            }

            return Command(
                update={
                    "step_index": idx + 1,
                    "retry_count": 0,
                    "log": [f"PASSED: {verdict.reason}"],
                    "step_history": [history_entry],  # appended via operator.add
                },
                goto="init_step",
            )

        ctx.logger.warning("Step %d failed: %s", idx, verdict.reason)
        return Command(
            update={"log": [f"FAILED: {verdict.reason}"]},
            goto="recover",
        )
