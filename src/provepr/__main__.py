"""CLI entry: python -m provepr <command>"""

from __future__ import annotations

import argparse

from provepr.connect import run_connect
from provepr.smoke import run_smoke


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="provepr",
        description="ProvePR — AI PR Reviewer (Hermes + Gemini)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("smoke", help="Sprint 1 health check (no API calls)")

    connect_parser = sub.add_parser(
        "connect",
        help="Sprint 2: verify GitHub + Jira read access",
    )
    connect_parser.add_argument(
        "--github",
        action="store_true",
        help="Only check GitHub",
    )
    connect_parser.add_argument(
        "--jira",
        action="store_true",
        help="Only check Jira",
    )

    args = parser.parse_args(argv)

    if args.command == "smoke":
        return run_smoke()

    if args.command == "connect":
        # Neither flag → check both; either flag → check only that side.
        if args.github or args.jira:
            return run_connect(github=args.github, jira=args.jira)
        return run_connect(github=True, jira=True)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
