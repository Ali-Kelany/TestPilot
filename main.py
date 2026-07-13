"""CLI entry point.

Loads a test case from a JSON file, wires up the event-driven
architecture, and runs the execution through the terminal.
"""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv

from src.adapters.cli import CLIAdapter
from src.adapters.database_listener import DatabaseListener
from src.config import ExecutionConfig, Settings
from src.infrastructure.database import Database
from src.loaders import load_from_json
from src.services.event_bus import EventBus
from src.services.execution import ExecutionService


async def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="LangGraph Web Agent Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m src.main -f tests.json --test-id 0
  python -m src.main -f tests.json --provider google --model gemini-pro
  python -m src.main -f tests.json --headless --verbose
        """,
    )
    parser.add_argument(
        "-f", "--file", required=True, help="Path to test case JSON file"
    )
    parser.add_argument(
        "--test-id",
        default="0",
        help="Index of the test case to run (default: 0)",
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run browser in headless mode"
    )
    parser.add_argument(
        "--provider",
        choices=["mistral", "google", "ollama", "openrouter", "llama_cpp"],
        default="google",
        help="LLM provider (default: google)",
    )
    parser.add_argument("--model", help="Model name (provider default if omitted)")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable coloured output"
    )

    args = parser.parse_args()

    # ── load test case ──────────────────────────────────────────
    try:
        test_cases = load_from_json(args.file)
        test_idx = int(args.test_id)
        if test_idx < 0 or test_idx >= len(test_cases):
            print(
                f"Error: Test index {test_idx} out of range. "
                f"Available: 0-{len(test_cases) - 1}"
            )
            return 1
        test_case = test_cases[test_idx]
    except FileNotFoundError:
        print(f"Error: Test file not found: {args.file}")
        return 1
    except Exception as exc:
        print(f"Error loading test file: {exc}")
        return 1

    # ── resolve settings ────────────────────────────────────────
    try:
        settings = Settings()
        # Validate the chosen provider has a key before we start
        settings.get_api_key(args.provider)
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    # ── build config ────────────────────────────────────────────
    config = ExecutionConfig(
        headless=args.headless,
        provider=args.provider,
        model=args.model,
    )

    # ── wire up event bus + adapters ──────────────────────────
    event_bus = EventBus()
    
    # CLI output
    cli = CLIAdapter(
        event_bus=event_bus,
        use_colors=not args.no_color,
        verbose=args.verbose,
    )
    cli.attach()

    # Database persistence
    db = Database(settings.db_path)
    db.create_tables()
    listener = DatabaseListener(event_bus, db)
    listener.attach()

    service = ExecutionService(event_bus, settings)

    # ── execute ─────────────────────────────────────────────────
    try:
        result = await service.execute(test_case, config)
        return 0 if result.result == "passed" else 1
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
        return 130
    except Exception as exc:
        print(f"\nFatal error: {exc}")
        return 1
    finally:
        cli.detach()
        listener.detach()


if __name__ == "__main__":
    exit(asyncio.run(main()))