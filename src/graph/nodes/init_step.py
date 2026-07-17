from __future__ import annotations

import time

from langchain.messages import RemoveMessage

from src.domain.events import StepStartedEvent
from src.graph.nodes.context import NodeContext
from src.graph.state import AgentState


class InitStepNode:
    def __init__(self, ctx: NodeContext) -> None:
        self._ctx = ctx

    async def __call__(self, state: AgentState) -> dict:
        ctx = self._ctx
        idx = state["step_index"]
        total = len(state["test_case"])

        if idx > total:     # Terminal case 
            ctx.logger.info("Test Completed: %d steps passed", total)
            return {
                "result": "passed",
                "log": [f"TEST PASSED: All {total} steps completed"],
            }

        step = state["test_case"].get_step(idx)
        action = step.action
        assertion = step.assertion

        log_msg = (
            f"----- Step {idx}/{total}: "
            f"action='{action}', assertion='{assertion}' -----"
        )
        ctx.logger.info(log_msg)

        await ctx.emit(
            StepStartedEvent(
                session_id=ctx.session_id,
                step_index=idx,
                total_steps=total,
                action=action,
                assertion=assertion,
            )
        )

        # Clear the previous step's conversation so the actor LLM starts fresh.
        cleanup = [
            RemoveMessage(id=msg.id) for msg in state.get("messages", []) if msg.id
        ]

        return {
            "step_action": action,
            "step_assertion": assertion,
            "step_start_time": time.time(),
            "loop_count": 0,
            "messages": cleanup,
            "log": [log_msg],
        }
