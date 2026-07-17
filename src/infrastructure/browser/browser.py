"""Async browser wrapper for web automation."""

from __future__ import annotations

import asyncio
import io
import time
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict, cast

import playwright.async_api as pw
from PIL import Image

from src.config import BrowserConfig

if TYPE_CHECKING:
    from logging import Logger


ScrollDirection = Literal["up", "down"]


class Mark(TypedDict):
    """Data returned for each marked element."""

    mark: str
    element: str
    role: str
    state: dict[str, bool]
    description: str
    isOffScreen: bool


class PageInfo(TypedDict):
    """Basic page information."""

    url: str
    title: str


class ViewportData(TypedDict):
    """Viewport and scroll information."""

    scroll_x: int
    scroll_y: int
    viewport_width: int
    viewport_height: int
    page_width: int
    page_height: int


# ── Exceptions ──────────────────────────────────────────────────


class BrowserError(Exception):
    """Base exception for browser operations."""


class NavigationError(BrowserError):
    """Navigation to URL failed."""


class ElementNotFoundError(BrowserError):
    """Element with specified mark not found."""


class ActionError(BrowserError):
    """Action on element failed."""


# ── JS helpers ──────────────────────────────────────────────────

_JS_DIR = Path(__file__).parent / "js"
_JS_CACHE: dict[str, str] = {}


def _load_js(filename: str) -> str:
    """Load a JavaScript file with caching."""
    if filename not in _JS_CACHE:
        path = _JS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"JS file not found: {path}")
        _JS_CACHE[filename] = path.read_text(encoding="utf-8")
    return _JS_CACHE[filename]


# ── Browser ─────────────────────────────────────────────────────


class Browser:
    """
    Async browser wrapper for web automation.

    Usage::

        async with await Browser.create(logger) as browser:
            await browser.goto("https://example.com")
            marks = await browser.mark_page()
            await browser.click(marks[0]["mark"])
    """

    __slots__ = (
        "_page",
        "_config",
        "_logger",
        "_playwright",
        "_owns_playwright",
    )

    def __init__(
        self,
        page: pw.Page,
        config: BrowserConfig,
        logger: Logger,
        playwright_instance: pw.Playwright | None = None,
        owns_playwright: bool = False,
    ) -> None:
        self._page = page
        self._config = config
        self._logger = logger
        self._playwright = playwright_instance
        self._owns_playwright = owns_playwright

    @classmethod
    async def create(
        cls,
        logger: Logger,
        config: BrowserConfig | None = None,
    ) -> Browser:
        """Create and initialise a browser instance.

        Args:
            logger: Logger instance for browser operations.
            config: Browser configuration settings.
        """
        config = config or BrowserConfig()

        logger.info("Starting browser...")

        playwright = await pw.async_playwright().start()
        browser = None
        context = None

        try:
            browser = await playwright.chromium.launch(headless=config.headless)
            context = await browser.new_context(
                bypass_csp=True,
                viewport={
                    "width": config.viewport_width,
                    "height": config.viewport_height,
                },
                locale=config.locale,
                timezone_id=config.timezone_id,
                has_touch=config.has_touch,
            )
            context.set_default_timeout(config.timeout_ms)

            for script in ("element_to_html_string.js", "mark_page.js"):
                await context.add_init_script(_load_js(script))

            page = await context.new_page()
            logger.info("Browser ready")

            return cls(
                page=page,
                config=config,
                logger=logger,
                playwright_instance=playwright,
                owns_playwright=True,
            )

        except Exception:
            if context:
                await context.close()
            if browser:
                await browser.close()
            await playwright.stop()
            raise

    async def __aenter__(self) -> Browser:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()

    async def close(self) -> None:
        """Release all browser resources."""
        page = self._page
        context = page.context if page else None
        browser = context.browser if context else None

        for resource, name in [
            (page, "page"),
            (context, "context"),
            (browser, "browser"),
        ]:
            if resource:
                try:
                    await resource.close()
                except Exception as e:
                    self._logger.warning("%s close error: %s", name, e)

        if self._owns_playwright and self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                self._logger.warning("Playwright stop error: %s", e)

    # ── Properties ──────────────────────────────────────────────

    @property
    def page(self) -> pw.Page:
        return self._page

    @property
    def url(self) -> str:
        return self._page.url

    # ── Navigation ──────────────────────────────────────────────

    async def goto(self, url: str) -> str:
        """Navigate to a URL."""
        self._logger.info("Navigating to %s", url)

        try:
            response = await self._page.goto(url, wait_until="domcontentloaded")
        except Exception as e:
            raise NavigationError(f"Failed to navigate to {url}: {e}") from e

        if response is None or not response.ok:
            status = response.status if response else "no response"
            raise NavigationError(f"Navigation failed with status {status}")

        await self._wait_stable()
        return f"Navigated to {url}"

    async def reload(self) -> str:
        """Reload the current page."""
        self._logger.info("Reloading page")

        try:
            await self._page.reload(wait_until="domcontentloaded")
        except Exception as e:
            raise NavigationError(f"Reload failed: {e}") from e

        await self._wait_stable()
        return f"Reloaded {self.url}"

    # ── Element interactions ────────────────────────────────────

    async def click(self, mark: str | int) -> str:
        """Click an element by its mark label."""
        target = await self._get_element(mark)
        html = await self._element_html(target)
        url_before = self.url

        self._logger.info("Clicking [%s]", mark)

        try:
            await target.click()
            await self._wait_stable()
        except Exception as e:
            raise ActionError(f"Click failed on [{mark}]: {e}") from e

        result = f"Clicked [{mark}]: {html}"
        if self.url != url_before:
            result += f" → {self.url}"
        return result

    async def fill(self, mark: str | int, value: str) -> str:
        """Fill a text input with a value."""
        target = await self._get_element(mark)
        html = await self._element_html(target)
        tag = await target.evaluate("el => el.tagName")

        if tag == "SELECT":
            raise ActionError(
                f"Element [{mark}] is a SELECT — use select() instead"
            )

        self._logger.info("Filling [%s] with '%s...'", mark, value[:20])

        try:
            input_type = await target.evaluate("el => el.type || ''")
            if tag == "INPUT" and input_type == "date":
                await target.fill(value)
            else:
                await target.clear()
                await target.press_sequentially(value, delay=10)

            actual = await target.input_value()
            if actual != value:
                self._logger.warning(
                    "Fill verification: expected '%s', got '%s'", value, actual
                )

        except Exception as e:
            raise ActionError(f"Fill failed on [{mark}]: {e}") from e

        return f"Filled [{mark}] with '{value}': {html}"

    async def select(self, mark: str | int, option: str) -> str:
        """Select an option from a dropdown."""
        target = await self._get_element(mark)

        self._logger.info("Selecting '%s' from [%s]", option, mark)

        try:
            selected = await target.select_option(option)
            return f"Selected '{selected[0] if selected else option}' from [{mark}]"
        except Exception as e:
            options = await target.evaluate(
                "el => Array.from(el.options || [], o => o.text || o.value)"
            )
            raise ActionError(
                f"Option '{option}' not found. Available: {', '.join(options)}"
            ) from e

    async def scroll(
        self, direction: ScrollDirection, pixels: int | None = None
    ) -> str:
        """Scroll the page up or down."""
        pixels = pixels or self._config.scroll_amount
        viewport = await self._get_viewport()

        max_scroll = viewport["page_height"] - viewport["viewport_height"]
        current = viewport["scroll_y"]

        if direction == "up":
            if current <= 0:
                return "Already at top of page"
            delta = -min(pixels, current)
        elif direction == "down":
            if current >= max_scroll - 10:
                return "Already at bottom of page"
            delta = min(pixels, max_scroll - current)
        else:
            raise ActionError(f"Invalid direction: {direction}")

        self._logger.info("Scrolling %s by %dpx", direction, abs(delta))

        await self._page.mouse.wheel(0, delta)
        await asyncio.sleep(0.3)

        return f"Scrolled {direction} by {abs(delta)}px"

    async def wait(self, seconds: float) -> str:
        """Wait for a specified duration."""
        self._logger.info("Waiting %ss", seconds)
        await asyncio.sleep(seconds)
        return f"Waited {seconds} seconds"

    # ── Page marking ────────────────────────────────────────────

    async def mark_page(self) -> list[Mark]:
        """Mark interactive elements and return their data."""
        await self._wait_stable()
        await self._ensure_scripts()
        result = await self._page.evaluate("window.markPage()")
        self._logger.debug("Marked %d elements", len(result))
        return cast(list[Mark], result)

    async def unmark_page(self) -> None:
        """Remove element marks from the page."""
        await self._ensure_scripts()
        await self._page.evaluate("window.unmarkPage()")

    # ── Page info ───────────────────────────────────────────────

    async def get_page_info(self) -> PageInfo:
        """Get current page URL and title."""
        title = await self._page.title()
        return {"url": self.url, "title": title}

    async def screenshot(self) -> bytes:
        """Capture a screenshot, resized according to config."""
        try:
            await self._wait_stable()
            raw = await self._page.screenshot()

            with Image.open(io.BytesIO(raw)) as img:
                target = (
                    self._config.screenshot_width,
                    self._config.screenshot_height,
                )
                if img.size != target:
                    img = img.resize(target, Image.Resampling.LANCZOS)

                if (
                    self._config.screenshot_format == "JPEG"
                    and img.mode in ("RGBA", "P")
                ):
                    img = img.convert("RGB")

                buffer = io.BytesIO()
                img.save(
                    buffer,
                    format=self._config.screenshot_format,
                    quality=self._config.screenshot_quality,
                    optimize=True,
                )
                return buffer.getvalue()

        except Exception as e:
            self._logger.error("Screenshot failed: %s", e)
            return b""

    # ── Private helpers ─────────────────────────────────────────

    async def _get_element(self, mark: str | int) -> pw.Locator:
        """Get element locator by mark, raising if not found."""
        mark = str(mark)
        locator = self._page.locator(f"[data-mark='{mark}']")

        if await locator.count() == 0:
            raise ElementNotFoundError(f"No element with mark [{mark}]")

        return locator.first

    async def _element_html(self, locator: pw.Locator) -> str:
        """Get HTML string representation of an element."""
        await self._ensure_scripts()
        return await locator.evaluate("el => window.elementToHtmlString(el)")

    async def _get_viewport(self) -> ViewportData:
        """Get viewport and page dimensions."""
        return cast(
            ViewportData,
            await self._page.evaluate(
                """() => ({
            scroll_x: Math.round(window.scrollX),
            scroll_y: Math.round(window.scrollY),
            viewport_width: window.innerWidth,
            viewport_height: window.innerHeight,
            page_width: document.documentElement.scrollWidth,
            page_height: document.documentElement.scrollHeight
        })"""
            ),
        )

    async def _wait_stable(self) -> None:
        """Wait for the page to stabilise (DOM stops changing)."""
        timeout_s = self._config.stability_timeout_ms / 1000
        interval = self._config.stability_interval_ms / 1000
        start = time.time()
        last_state = None

        try:
            await self._page.wait_for_load_state(
                "load", timeout=self._config.stability_timeout_ms
            )
        except Exception:
            pass

        while time.time() - start < timeout_s:
            try:
                state = await self._page.evaluate(
                    """() => ({
                    nodes: document.querySelectorAll('*').length,
                    text: document.body?.innerText.length || 0
                })"""
                )
            except Exception:
                await asyncio.sleep(interval)
                continue

            if last_state and state == last_state:
                return

            last_state = state
            await asyncio.sleep(interval)

    async def _ensure_scripts(self) -> None:
        """Ensure helper scripts are loaded in the page."""
        for attempt in range(3):
            try:
                loaded = await self._page.evaluate(
                    "() => typeof window.markPage === 'function' "
                    "&& typeof window.elementToHtmlString === 'function'"
                )
                if loaded:
                    return

                for script in (
                    "element_to_html_string.js",
                    "mark_page.js",
                ):
                    await self._page.add_script_tag(
                        content=_load_js(script)
                    )

                await self._page.wait_for_function(
                    "() => typeof window.markPage === 'function'",
                    timeout=2000,
                )
                return

            except Exception as e:
                if attempt == 2:
                    raise BrowserError(
                        f"Failed to inject scripts after 3 attempts: {e}"
                    ) from e
                await asyncio.sleep(0.1)