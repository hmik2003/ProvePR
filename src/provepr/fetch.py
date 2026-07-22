"""Sprint 3 fetch — pull PR diff + Jira PRD text for local preview."""

from __future__ import annotations

import os

import httpx

from provepr.config import load_env, require_github_settings, require_jira_settings
from provepr.github_client import GitHubClient
from provepr.jira_client import JiraClient
from provepr.jira_text import issue_prd_text

PREVIEW_LINES = 40


def _preview(text: str, max_lines: int = PREVIEW_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    shown = "\n".join(lines[:max_lines])
    return f"{shown}\n... ({len(lines) - max_lines} more lines)"


def resolve_targets(
    *,
    repo: str | None,
    pr: int | None,
    ticket: str | None,
) -> tuple[str, int, str]:
    resolved_repo = (repo or os.getenv("GITHUB_TEST_REPO") or "").strip()
    pr_raw = pr if pr is not None else os.getenv("GITHUB_TEST_PR_NUMBER")
    resolved_ticket = (ticket or os.getenv("JIRA_TEST_TICKET") or "").strip()

    missing: list[str] = []
    if not resolved_repo:
        missing.append("repo (--repo or GITHUB_TEST_REPO)")
    if pr_raw is None or str(pr_raw).strip() == "":
        missing.append("pr (--pr or GITHUB_TEST_PR_NUMBER)")
    if not resolved_ticket:
        missing.append("ticket (--ticket or JIRA_TEST_TICKET)")
    if missing:
        raise ValueError("Missing required fetch targets: " + ", ".join(missing))

    try:
        resolved_pr = int(str(pr_raw).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("GITHUB_TEST_PR_NUMBER / --pr must be an integer") from exc

    return resolved_repo, resolved_pr, resolved_ticket


def run_fetch(
    *,
    repo: str | None = None,
    pr: int | None = None,
    ticket: str | None = None,
) -> int:
    print("=== ProvePR — Sprint 3 Fetch ===")
    load_env()
    try:
        full_name, pr_number, ticket_key = resolve_targets(
            repo=repo, pr=pr, ticket=ticket
        )
    except ValueError as exc:
        print(f"Fetch FAIL: {exc}")
        print("Set targets in .env or pass --repo / --pr / --ticket.")
        return 1

    try:
        gh_settings = require_github_settings()
        jira_settings = require_jira_settings()

        with GitHubClient(gh_settings) as gh:
            pull = gh.get_pull_request(full_name, pr_number)
            diff = gh.get_pull_request_diff(full_name, pr_number)

        with JiraClient(jira_settings) as jira:
            issue = jira.get_issue(ticket_key)

        prd = issue_prd_text(issue)
    except ValueError as exc:
        print(f"Fetch FAIL: {exc}")
        return 1
    except httpx.HTTPStatusError as exc:
        print(f"Fetch FAIL: HTTP {exc.response.status_code}")
        return 1
    except httpx.RequestError as exc:
        print(f"Fetch FAIL: request error ({exc.__class__.__name__})")
        return 1

    print(f"\nGitHub PR #{pull.get('number')} — {pull.get('title', '(no title)')}")
    print(f"  URL   : {pull.get('html_url', '')}")
    print(f"  Diff  : {len(diff.splitlines())} lines, {len(diff)} chars")
    print("  --- diff preview ---")
    print(_preview(diff or "(empty diff)"))

    fields = issue.get("fields") or {}
    print(f"\nJira {issue.get('key', ticket_key)} — {fields.get('summary', '(no summary)')}")
    print("  --- PRD / requirements preview ---")
    print(_preview(prd or "(no description text on this ticket)"))

    print("\n=== Sprint 3 OK ===")
    print("Working product this sprint: fetch PR diff + Jira PRD text.")
    print("Next sprint: Hermes + Gemini local AI review.")
    return 0
