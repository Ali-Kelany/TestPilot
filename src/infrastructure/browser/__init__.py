"""Browser automation infrastructure."""

from src.infrastructure.browser.browser import (
    ActionError,
    Browser,
    BrowserError,
    ElementNotFoundError,
    Mark,
    NavigationError,
    PageInfo,
    ScrollDirection,
    ViewportData,
)

__all__ = [
    "Browser",
    "BrowserError",
    "NavigationError",
    "ElementNotFoundError",
    "ActionError",
    "ScrollDirection",
    "Mark",
    "PageInfo",
    "ViewportData",
]