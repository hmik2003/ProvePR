"""CLI entry: python -m tickettrace <command>"""

from __future__ import annotations

import argparse
import sys

from tickettrace.smoke import run_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tickettrace",
        description="TicketTrace — AI PR reviewer (Hermes + Gemini)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke", help="Sprint 1 health check (no API calls)")

    args = parser.parse_args(argv)

    if args.command == "smoke":
        return run_smoke()

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
