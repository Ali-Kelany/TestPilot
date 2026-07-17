"""Minimal token usage tracker — accumulates counts across all LLM calls."""

from langchain_core.callbacks import BaseCallbackHandler


class TokenTracker(BaseCallbackHandler):
    """LangChain callback that sums usage_metadata across all LLM invocations."""

    def __init__(self) -> None:
        self.total_tokens = 0

    def on_llm_end(self, response, **kwargs) -> None:
        """Called by LangChain after every model .ainvoke() completes."""
        for gen in response.generations:
            for chunk in gen:
                meta = chunk.message.usage_metadata
                if meta:
                    self.total_tokens += meta.get("total_tokens", 0)
