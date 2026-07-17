from __future__ import annotations

from typing import List

from langchain_core.tools import tool
from langgraph.types import Command

from src.infrastructure.browser import Browser, ScrollDirection


def create_browser_tools(browser: Browser) -> List:
    """Return browser interaction tools bound to *browser*."""

    @tool
    async def click(label: int) -> str:
        """Click element [N]. Automatically waits for page load/stability."""
        return await browser.click(str(label))

    @tool
    async def fill(label: int, value: str) -> str:
        """Fill input [N] with text. Clears existing content first."""
        return await browser.fill(str(label), value)

    @tool
    async def select(label: int, option: str) -> str:
        """Select an option from a dropdown identified by its numerical label."""
        return await browser.select(str(label), option)

    @tool
    async def goto(url: str) -> str:
        """Navigate to a URL."""
        return await browser.goto(url)

    @tool
    async def reload() -> str:
        """Reload the current page. Use if the page appears stuck or broken."""
        return await browser.reload()

    @tool
    async def scroll(direction: ScrollDirection, pixels: int = 450) -> str:
        """Scroll the page up or down."""
        return await browser.scroll(direction, pixels)

    @tool
    async def wait(seconds: float) -> str:
        """Explicit wait. Use only if the page is still loading after an action."""
        return await browser.wait(seconds)

    @tool
    async def save_to_memory(key: str, value: str) -> Command:
        """Save data to persistent memory for use in later steps.

        Examples: IDs, generated usernames, confirmation numbers.

        Returns a Command so SequentialToolExecutor merges the value directly
        into AgentState.memory — no executor-side parsing needed.
        """
        return Command(
            update={"memory": {key: value}},
        )

    @tool
    async def finish_task(summary: str) -> Command:
        """Call ONLY when the current step action is fully achieved.

        Include this as the LAST tool call after all browser interactions
        for the current step are complete.  It signals the graph to route
        directly to verification, skipping a re-observation cycle.
        """
        return Command(
            update={"log": [f"Step action completed: {summary}"]},
            goto="verify",
        )

    return [click, fill, select, goto, reload, scroll, wait, save_to_memory, finish_task]
