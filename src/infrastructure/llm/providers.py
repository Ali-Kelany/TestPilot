"""LLM provider factory.

Every model constructor receives its API key from a :class:`Settings`
instance — **no secrets in source code**.

Usage::

    from src.config import Settings
    from src.infrastructure.llm.providers import get_chat_model, ModelProvider

    settings = Settings()
    model = get_chat_model(settings, ModelProvider.MISTRAL)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_mistralai import ChatMistralAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.config import Settings


class ModelProvider(Enum):
    """Supported LLM providers."""

    MISTRAL = "mistral"
    GOOGLE = "google"
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    LLAMA_CPP = "llama_cpp"


PROVIDER_DEFAULTS: dict[ModelProvider, str] = {
    ModelProvider.MISTRAL: "mistral-large-2512",
    ModelProvider.GOOGLE: "gemma-4-31b-it",
    ModelProvider.OLLAMA: "ministral-3:3b",
    ModelProvider.OPENROUTER: "sourceful/riverflow-v2-pro",
    ModelProvider.LLAMA_CPP: "local-model"
}

DEFAULT_TEMPERATURE = 0.0


def get_chat_model(
    settings: Settings,
    provider: ModelProvider | str = ModelProvider.GOOGLE,
    model: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Any:
    """Create a base chat model for the given provider.

    API keys are read from *settings*, never hard-coded.

    Args:
        settings: Application settings with API keys.
        provider: LLM provider enum or string name.
        model: Model name (uses provider default when ``None``).
        temperature: Sampling temperature.

    Returns:
        Configured chat model instance.

    Raises:
        ValueError: If the provider is unsupported or its API key is missing.
    """
    if isinstance(provider, str):
        provider = ModelProvider(provider.lower())

    model_name = model or PROVIDER_DEFAULTS[provider]

    if provider == ModelProvider.MISTRAL:
        return ChatMistralAI(
            model=model_name,
            temperature=temperature,
            api_key=settings.get_api_key("mistral"),
        )

    if provider == ModelProvider.GOOGLE:
        return ChatGoogleGenerativeAI(
            model=model_name,
            temperature=temperature,
            google_api_key=settings.get_api_key("google"),
        )

    if provider == ModelProvider.OLLAMA:
        return ChatOllama(
            model=model_name,
            temperature=temperature,
        )

    if provider == ModelProvider.OPENROUTER:
        return ChatOpenAI(
            model=model_name,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
            api_key=settings.get_api_key("openrouter"),
        )
    
    if provider == ModelProvider.LLAMA_CPP:
        return ChatOpenAI(
            model=model_name,
            base_url="http://127.0.0.1:8080/v1",
            api_key="not-needed"
        )

    raise ValueError(f"Unsupported provider: {provider}")


def get_tool_model(
    settings: Settings,
    tools: list,
    provider: ModelProvider | str = ModelProvider.GOOGLE,
    model: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Any:
    """Create a chat model with *tools* bound.

    Args:
        settings: Application settings.
        tools: Tools to bind to the model.
        provider: LLM provider.
        model: Model name.
        temperature: Sampling temperature.
    """
    return get_chat_model(settings, provider, model, temperature).bind_tools(
        tools
    )


def get_structured_model(
    settings: Settings,
    schema: Any,
    provider: ModelProvider | str = ModelProvider.GOOGLE,
    model: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
) -> Any:
    """Create a chat model with structured output.

    Args:
        settings: Application settings.
        schema: Pydantic model for structured output.
        provider: LLM provider.
        model: Model name.
        temperature: Sampling temperature.
    """
    return get_chat_model(
        settings, provider, model, temperature
    ).with_structured_output(schema)