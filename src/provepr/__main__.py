"""CLI entry: python -m provepr <command>"""

from __future__ import annotations

import argparse

from provepr.connect import run_connect
from provepr.fetch import run_fetch
from provepr.jira_key import extract_jira_key
from provepr.prd_gate_cli import run_prd_gate
from provepr.review import run_review
from provepr.server import run_server
from provepr.skip_notify import run_skip_notify
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

    review_parser = sub.add_parser(
        "review",
        help="Sprint 4/5: Gemini review; optional --post to GitHub/Slack",
    )
    review_parser.add_argument("--repo", help="owner/name (or GITHUB_TEST_REPO)")
    review_parser.add_argument("--pr", type=int, help="PR number (or GITHUB_TEST_PR_NUMBER)")
    review_parser.add_argument("--ticket", help="Jira key (or JIRA_TEST_TICKET)")
    review_parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually call Gemini once (without this flag = free dry-run)",
    )
    review_parser.add_argument(
        "--post",
        action="store_true",
        help="After review, post GitHub PR comment + Slack DM (or stub); requires --yes",
    )

    sub.add_parser(
        "serve",
        help="Sprint 6: HTTP trigger server (GET /health, POST /v1/review)",
    )

    jira_parser = sub.add_parser(
        "jira-key",
        help="Sprint 7: extract Jira key from title/branch/body text",
    )
    jira_parser.add_argument("--title", default="")
    jira_parser.add_argument("--branch", default="")
    jira_parser.add_argument("--body", default="")

    gate_parser = sub.add_parser(
        "prd-gate",
        help="Soft PRD quality gate for Story tickets (Jira comment + Slack; no transitions)",
    )
    gate_parser.add_argument("--ticket", required=True, help="Jira issue key (e.g. PROV-10)")
    gate_parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Do not Slack-DM the gate verdict (default: notify QA)",
    )
    gate_parser.add_argument(
        "--no-comment",
        action="store_true",
        help="Do not leave a Jira ticket comment for PMs (default: comment)",
    )

    skip_parser = sub.add_parser(
        "skip-notify",
        help="Notify QA that review was skipped (no ticket / policy); no Gemini",
    )
    skip_parser.add_argument("--repo", required=True, help="owner/name")
    skip_parser.add_argument("--pr", type=int, required=True, help="PR number")
    skip_parser.add_argument(
        "--reason",
        default="none",
        choices=["none", "multiple"],
        help="Why review was skipped",
    )
    skip_parser.add_argument("--title", default="", help="PR title (for the message)")
    skip_parser.add_argument("--pr-url", default="", help="PR html URL")
    skip_parser.add_argument(
        "--detail",
        default="",
        help="Extra detail (e.g. comma-separated keys when reason=multiple)",
    )
    skip_parser.add_argument(
        "--no-comment",
        action="store_true",
        help="Slack only — do not post a GitHub skip comment",
    )

    args = parser.parse_args(argv)

    if args.command == "smoke":
        return run_smoke()

    if args.command == "connect":
        if args.github or args.jira:
            return run_connect(github=args.github, jira=args.jira)
        return run_connect(github=True, jira=True)

    if args.command == "fetch":
        return run_fetch(repo=args.repo, pr=args.pr, ticket=args.ticket)

    if args.command == "review":
        return run_review(
            repo=args.repo,
            pr=args.pr,
            ticket=args.ticket,
            yes=args.yes,
            post=args.post,
        )

    if args.command == "serve":
        return run_server()

    if args.command == "jira-key":
        key = extract_jira_key(args.title, args.branch, args.body)
        if not key:
            return 1
        print(key)
        return 0

    if args.command == "prd-gate":
        return run_prd_gate(
            ticket=args.ticket,
            notify=not args.no_notify,
            comment=not args.no_comment,
        )

    if args.command == "skip-notify":
        return run_skip_notify(
            repo=args.repo,
            pr=args.pr,
            reason=args.reason,
            title=args.title,
            pr_url=args.pr_url,
            detail=args.detail,
            comment=not args.no_comment,
        )

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
