"""Centralized configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


class Settings:
    """
    Application settings read from environment variables.

    API keys are loaded at construction time. Call get_api_key(provider)
    to retrieve one — raises ValueError immediately if the required
    variable is not set.
    """

    _ENV_KEYS: dict[str, str] = {
        "mistral": "MISTRAL_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }

    def __init__(self) -> None:
        self._api_keys: dict[str, str] = {}
        self.db_path: str = os.environ.get("DATABASE_PATH", "data/web_agent.db")
        self.max_action_loops = int(os.environ.get("AGENT_MAX_LOOPS", 10))
        self.max_step_retries = int(os.environ.get("AGENT_MAX_RETRIES", 2))

        for provider, env_var in self._ENV_KEYS.items():
            value = os.environ.get(env_var)
            if value:
                self._api_keys[provider] = value

    def get_api_key(self, provider: str) -> str:
        """Return the API key for provider, or raise if unset."""
        provider = provider.lower()
        if provider == "ollama" or provider == "llama_cpp":
            return ""

        key = self._api_keys.get(provider)
        if not key:
            env_var = self._ENV_KEYS.get(provider, f"{provider.upper()}_API_KEY")
            raise ValueError(
                f"API key for '{provider}' is not set. "
                f"Set the {env_var} environment variable."
            )
        return key

    @property
    def log_level(self) -> str:
        return os.environ.get("LOG_LEVEL", "INFO").upper()

    @property
    def log_format(self) -> Literal["json", "text"]:
        fmt = os.environ.get("LOG_FORMAT", "text").lower()
        return fmt if fmt in ("json", "text") else "text"



@dataclass(frozen=True)
class BrowserConfig:
    """Browser and screenshot settings."""

    headless: bool = True
    viewport_width: int = 1280
    viewport_height: int = 720
    timeout_ms: int = 30_000
    locale: str = "en-US"
    timezone_id: str = "America/New_York"
    has_touch: bool = False

    screenshot_width: int = 1280
    screenshot_height: int = 720
    screenshot_format: Literal["PNG", "JPEG", "WEBP"] = "JPEG"
    screenshot_quality: int = 50

    stability_timeout_ms: int = 3000
    stability_interval_ms: int = 300

    scroll_amount: int = 450


@dataclass
class ExecutionConfig:
    """Per-run execution settings."""

    headless: bool = True
    provider: str = "google"
    model: str | None = None
    recursion_limit: int = 200

    def to_browser_config(self) -> BrowserConfig:
        return BrowserConfig(headless=self.headless)