from __future__ import annotations

import base64

from langchain.messages import AIMessage, HumanMessage, SystemMessage

from src.domain.events import ObservationEvent, ToolCalledEvent
from src.infrastructure.llm.prompts import ACTOR_SYSTEM, format_observation
from src.graph.nodes.context import NodeContext
from src.graph.state import AgentState


TOOL_PRIORITY = {
    "scroll": 1,
    "wait": 2,
    "fill": 3,
    "select": 3,
    "click": 4,
    "save_to_memory": 5,
    "finish_task": 6,
    "goto": 7,
    "reload": 7,
}


class ActNode:
    def __init__(self, ctx: NodeContext) -> None:
        self._ctx = ctx

    async def __call__(self, state: AgentState) -> dict:
        ctx = self._ctx
        loop = state["loop_count"]

        if loop >= ctx.max_action_loops:
            ctx.logger.warning(
                "Step %d: Exceeded maximum action loops (%d).",
                state["step_index"],
                ctx.max_action_loops,
            )
            return {
                "messages": [
                    AIMessage(
                        content="Action loop limit reached — proceeding to verification."
                    )
                ],
                "log": ["Action loop limit reached — moving to verification"],
            }

        # Phase 1: Observe
        ctx.logger.info("Step %d: Observing the current state...", state["step_index"])

        marks = await ctx.browser.mark_page()
        screenshot = await ctx.browser.screenshot()
        page_info = await ctx.browser.get_page_info()

        elements_list: list[str] = []
        for m in marks:
            if m.get("isOffScreen"):
                continue

            state_flags: list[str] = []
            if m.get("state", {}).get("disabled"):
                state_flags.append("DISABLED")
            if "checked" in m.get("state", {}):
                state_flags.append(f"CHECKED:{m['state']['checked']}")
            if "expanded" in m.get("state", {}):
                state_flags.append(f"EXPANDED:{m['state']['expanded']}")

            flags_str = f" [{', '.join(state_flags)}]" if state_flags else ""
            elements_list.append(f"[{m['mark']}] {m['element']}{flags_str}")

        elements_text = (
            "\n".join(elements_list)
            if elements_list
            else "(no interactive elements visible)"
        )

        await ctx.emit(
            ObservationEvent(
                session_id=ctx.session_id,
                page_url=page_info.get("url", ""),
                page_title=page_info.get("title", ""),
                element_count=len(elements_list),
                screenshot_size=len(screenshot),
            )
        )

        b64 = base64.b64encode(screenshot).decode()
        current_obs = HumanMessage(
            id=f"obs_{loop}",
            content=[
                {
                    "type": "text",
                    "text": format_observation(
                        action=state["step_action"],
                        assertion=state["step_assertion"],
                        memory=state.get("memory", {}),
                        elements=elements_text,
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ],
        )

        # Phase 2: Plan
        # Replace screenshots in older HumanMessages with a text-only placeholder
        # to keep the context window manageable. The current observation always
        # carries its full multimodal content.
        compressed: list = []
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                compressed.append(
                    HumanMessage(
                        content=format_observation(
                            action=state["step_action"],
                            assertion=state["step_assertion"],
                            memory=state.get("memory", {}),
                            elements="[compressed — see latest observation]",
                        )
                    )
                )
            else:
                compressed.append(msg)

        # Build the message list sent to the LLM.
        # Loop 0: history is empty → prepend SystemMessage.
        # Loop N: SystemMessage is already in state["messages"] (added by loop 0).
        if loop == 0:
            llm_input: list = [SystemMessage(content=ACTOR_SYSTEM), current_obs]
        else:
            llm_input = compressed + [current_obs]

        response: AIMessage = await ctx.actor_model.ainvoke(llm_input)

        if response.tool_calls:
            response.tool_calls.sort(key=lambda c: TOOL_PRIORITY.get(c["name"], 99))

        if response.tool_calls:
            for call in response.tool_calls:
                await ctx.emit(
                    ToolCalledEvent(
                        session_id=ctx.session_id,
                        tool_name=call["name"],
                        tool_args=call["args"],
                        tool_call_id=call["id"],
                    )
                )

        # Build state update 
        # Loop 0: add [SystemMessage, current_obs, response] - starts the history.
        # Loop N: add [current_obs, response] - SystemMessage already in history.
        if loop == 0:
            new_messages: list = [SystemMessage(content=ACTOR_SYSTEM, id="system"), current_obs, response]
        else:
            new_messages = [current_obs, response]

        updates: dict = {
            "messages": new_messages,
            "screenshot": screenshot,
            "page_url": page_info.get("url"),
            "page_title": page_info.get("title"),
        }

        if response.tool_calls:
            updates["loop_count"] = loop + 1

        return updates
