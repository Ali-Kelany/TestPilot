from __future__ import annotations

from logging import Logger
from typing import Literal

from langchain.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from src.config import Settings
from src.domain.events import ToolResultEvent
from src.infrastructure.browser import Browser
from src.infrastructure.llm.providers import (
    ModelProvider,
    get_structured_model,
    get_tool_model,
)
from src.services.event_bus import EventBus
from src.graph.nodes.act import ActNode
from src.graph.nodes.context import NodeContext
from src.graph.nodes.init_step import InitStepNode
from src.graph.nodes.recover import RecoverNode, RecoveryDecision
from src.graph.nodes.token_tracker import TokenTracker
from src.graph.nodes.verify import AssertionResult, VerifyNode
from src.graph.state import AgentState
from src.graph.tools import create_browser_tools


class SequentialToolExecutor:
    """Execute tools one-at-a-time and emit ToolResultEvents."""

    def __init__(self, tools: list, ctx: NodeContext) -> None:
        self._tools_by_name = {t.name: t for t in tools}
        self._ctx = ctx

    async def __call__(
        self, state: AgentState
    ) -> Command[Literal["act", "verify"]]:
        last_msg = state["messages"][-1]
        ctx = self._ctx
        tool_messages: list[ToolMessage] = []
        state_updates: dict = {}

        for call in last_msg.tool_calls:
            tool = self._tools_by_name.get(call["name"])

            if not tool:
                output = f"Error: unknown tool '{call['name']}'"
                success = False
            else:
                try:
                    result = await tool.ainvoke(call["args"])
                    if isinstance(result, Command) and result.goto is not None:
                        # finish_task - route directly to verify.
                        if result.update:
                            state_updates.update(result.update)

                        content = (f"Task finished: {call['args'].get('summary', '')}")
                        tool_messages.append(ToolMessage(
                            content=content,
                            tool_call_id=call["id"],
                            name=call["name"],
                            status="success",
                            id=call["id"],
                        ))
                        await ctx.emit(ToolResultEvent(
                            session_id=ctx.session_id,
                            tool_name=call["name"],
                            tool_call_id=call["id"],
                            result=content,
                            success=True,
                        ))
                        return Command(
                            update={"messages": tool_messages, **state_updates},
                            goto="verify",
                        )
                    if isinstance(result, Command):
                        # save_to_memory - merge state update.
                        if result.update:
                            for k, v in result.update.items():
                                if (
                                    k in state_updates
                                    and isinstance(v, dict)
                                    and isinstance(state_updates[k], dict)
                                ):
                                    state_updates[k].update(v)
                                else:
                                    state_updates[k] = v
                        
                        args = call.get("args", {})
                        output = (f"Saved {args['key']}='{args['value']}' to memory")
                        success = True
                    else:
                        output = str(result)
                        success = True
                except Exception as e:
                    ctx.logger.error("Step %d: Tool error: %s", state["step_index"], e)
                    output = f"Error: {e}"
                    success = False

            tool_messages.append(ToolMessage(
                content=output,
                tool_call_id=call["id"],
                name=call["name"],
                status="error" if not success else "success",
                id=call["id"],
            ))

            await ctx.emit(ToolResultEvent(
                session_id=ctx.session_id,
                tool_name=call["name"],
                tool_call_id=call["id"],
                result=output,
                success=success,
            ))

        return Command(
            update={"messages": tool_messages, **state_updates},
            goto="act",
        )


# Routing functions 

def route_init_step(state: AgentState) -> Literal["act", "__end__"]:
    """Advance to act, or end the run when all steps are complete."""
    return END if state["step_index"] > len(state["test_case"]) else "act"


def route_act(state: AgentState) -> Literal["tools", "verify"]:
    """Execute tools if the LLM requested them; otherwise verify the step."""
    last = state["messages"][-1]
    has_tools = isinstance(last, AIMessage) and bool(last.tool_calls)
    return "tools" if has_tools else "verify"


# Graph factory

def create_agent(
    browser: Browser,
    logger: Logger,
    settings: Settings,
    event_bus: EventBus | None = None,
    session_id: str = "",
    provider: ModelProvider | str = ModelProvider.GOOGLE,
    model: str | None = None,
    token_tracker: TokenTracker | None = None,
):
    """Build and compile the web-testing agent graph.

    Args:
        browser: Browser instance for page interactions.
        logger: File logger for the session.
        settings: Application settings (API keys, limits).
        event_bus: Optional bus for UI / persistence events.
        session_id: Correlation ID emitted with every event.
        provider: LLM provider.
        model: Model name (provider default when ``None``).
        token_tracker: Optional callback handler to count LLM tokens.

    Returns:
        Compiled LangGraph ready for ``.astream()`` or ``.ainvoke()``.
    """
    if isinstance(provider, str):
        provider = ModelProvider(provider.lower())

    tools = create_browser_tools(browser)

    actor_model = get_tool_model(settings, tools, provider, model)
    assertor_model = get_structured_model(settings, AssertionResult, provider, model)
    recovery_model = get_structured_model(settings, RecoveryDecision, provider, model)

    if token_tracker is not None:
        actor_model = actor_model.with_config({"callbacks": [token_tracker]})
        assertor_model = assertor_model.with_config({"callbacks": [token_tracker]})
        recovery_model = recovery_model.with_config({"callbacks": [token_tracker]})

    ctx = NodeContext(
        browser=browser,
        logger=logger,
        event_bus=event_bus,
        session_id=session_id,
        actor_model=actor_model,
        assertor_model=assertor_model,
        recovery_model=recovery_model,
        max_action_loops=settings.max_action_loops,
        max_step_retries=settings.max_step_retries,
    )

    builder = StateGraph(AgentState)

    builder.add_node("init_step", InitStepNode(ctx))
    builder.add_node("act", ActNode(ctx))
    builder.add_node("tools", SequentialToolExecutor(tools, ctx))
    builder.add_node("verify", VerifyNode(ctx))
    builder.add_node("recover", RecoverNode(ctx))

    builder.add_edge(START, "init_step")

    builder.add_conditional_edges("init_step", route_init_step)
    builder.add_conditional_edges("act", route_act)

    return builder.compile()
