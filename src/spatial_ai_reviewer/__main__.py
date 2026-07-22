"""CLI entry: python -m spatial_ai_reviewer <command>"""

from __future__ import annotations

import argparse
import sys

from spatial_ai_reviewer.smoke import run_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spatial_ai_reviewer",
        description="AI PR reviewer (Hermes + Gemini) — local tooling",
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
