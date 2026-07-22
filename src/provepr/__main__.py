"""CLI entry: python -m provepr <command>"""

from __future__ import annotations

import argparse

from provepr.connect import run_connect
from provepr.fetch import run_fetch
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

    fetch_parser = sub.add_parser(
        "fetch",
        help="Sprint 3: fetch PR diff + Jira PRD text",
    )
    fetch_parser.add_argument("--repo", help="owner/name (or GITHUB_TEST_REPO)")
    fetch_parser.add_argument("--pr", type=int, help="PR number (or GITHUB_TEST_PR_NUMBER)")
    fetch_parser.add_argument("--ticket", help="Jira key (or JIRA_TEST_TICKET)")

    args = parser.parse_args(argv)

    if args.command == "smoke":
        return run_smoke()

    if args.command == "connect":
        if args.github or args.jira:
            return run_connect(github=args.github, jira=args.jira)
        return run_connect(github=True, jira=True)

    if args.command == "fetch":
        return run_fetch(repo=args.repo, pr=args.pr, ticket=args.ticket)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
