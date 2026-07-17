from __future__ import annotations

import base64
import time
from typing import Literal

from langchain.messages import HumanMessage, RemoveMessage, SystemMessage
from langgraph.graph import END
from langgraph.types import Command
from pydantic import BaseModel, Field

from src.domain.events import RecoveryEvent, StepCompletedEvent
from src.infrastructure.llm.prompts import RECOVERY_SYSTEM, format_recovery_prompt
from src.graph.nodes.context import NodeContext
from src.graph.state import AgentState


class RecoveryDecision(BaseModel):
    """Structured output from the recovery model."""

    should_retry: bool = Field(description="Whether to retry the step.")
    reason: str = Field(description="Explanation of the decision.")


class RecoverNode:
    """Analyse the failure, consult the recovery model, and either
    retry the step (→ act) or mark the test as failed (→ END)."""

    def __init__(self, ctx: NodeContext) -> None:
        self._ctx = ctx

    async def __call__(
        self, state: AgentState
    ) -> Command[Literal["act", "__end__"]]:
        ctx = self._ctx
        retries = state["retry_count"]
        idx = state["step_index"]
        max_retries = ctx.max_step_retries
        # step_start_time lives in state — no ctx mutation needed.
        duration = time.time() - state["step_start_time"]

        # Helper: emit events and return a failed-test Command
        async def _abort(reason: str) -> Command:
            await ctx.emit(
                RecoveryEvent(
                    session_id=ctx.session_id,
                    retry_count=retries,
                    max_retries=max_retries,
                    should_retry=False,
                    reason=reason,
                )
            )
            await ctx.emit(
                StepCompletedEvent(
                    session_id=ctx.session_id,
                    step_index=idx,
                    passed=False,
                    reason=reason,
                    duration_seconds=duration,
                    retry_count=retries,
                    screenshot_observation=state.get("screenshot"),
                    screenshot_verification=None,
                )
            )
            return Command(
                update={
                    "result": "failed",
                    "log": [f"TEST FAILED: Step {idx} — {reason}"],
                },
                goto=END,
            )

        # Retry budget exhausted
        if retries >= max_retries:
            ctx.logger.error(
                "Step %d failed after %d retries.", idx, retries
            )
            return await _abort("Exceeded retry limit")

        # Ask the recovery model
        prompt = format_recovery_prompt(
            action=state["step_action"],
            assertion=state["step_assertion"],
            log_entries=state.get("log", []),
        )

        human_content: list = [{"type": "text", "text": prompt}]
        if state.get("screenshot"):
            b64 = base64.b64encode(state["screenshot"]).decode()
            human_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                }
            )

        try:
            decision: RecoveryDecision = await ctx.recovery_model.ainvoke(
                [
                    SystemMessage(content=RECOVERY_SYSTEM),
                    HumanMessage(content=human_content),
                ]
            )
        except Exception as e:
            ctx.logger.error("Step %d: Recovery analysis error: %s", idx, e)
            decision = RecoveryDecision(should_retry=False, reason=str(e))

        # Retry
        if decision.should_retry:
            next_retry = retries + 1
            ctx.logger.info(
                "Retrying step %d (%d/%d): %s",
                idx,
                next_retry,
                max_retries,
                decision.reason,
            )

            await ctx.emit(
                RecoveryEvent(
                    session_id=ctx.session_id,
                    retry_count=next_retry,
                    max_retries=max_retries,
                    should_retry=True,
                    reason=decision.reason,
                )
            )

            cleanup = [
                RemoveMessage(id=m.id)
                for m in state.get("messages", [])
                if m.id
            ]

            return Command(
                update={
                    "retry_count": next_retry,
                    "loop_count": 0,
                    "messages": cleanup,
                    "log": [
                        f"RETRY ({next_retry}/{max_retries}): {decision.reason}"
                    ],
                },
                goto="act",
            )

        # Unrecoverable failure
        ctx.logger.error("Step %d unrecoverable: %s", idx, decision.reason)
        return await _abort(decision.reason)
