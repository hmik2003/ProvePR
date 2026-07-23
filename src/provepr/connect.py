"""Sprint 2 connect check — verify GitHub + Jira read access."""

from __future__ import annotations

import os

import httpx

from provepr.config import require_github_settings, require_jira_settings
from provepr.github_client import GitHubClient
from provepr.jira_client import JiraClient


def _check_github() -> None:
    settings = require_github_settings()
    with GitHubClient(settings) as client:
        user = client.get_authenticated_user()
        login = user.get("login", "?")
        print(f"GitHub OK as @{login}")

        repo_name = (os.getenv("GITHUB_TEST_REPO") or "").strip()
        if repo_name:
            repo = client.get_repo(repo_name)
            visibility = "private" if repo.get("private") else "public"
            print(f"  Repo peek  : {repo.get('full_name', repo_name)} ({visibility})")


def _check_jira() -> None:
    settings = require_jira_settings()
    with JiraClient(settings) as client:
        me = client.get_myself()
        name = me.get("displayName") or me.get("emailAddress") or "?"
        print(f"Jira OK as {name}")

        ticket = (os.getenv("JIRA_TEST_TICKET") or "").strip()
        if ticket:
            issue = client.get_issue(ticket)
            fields = issue.get("fields") or {}
            summary = fields.get("summary") or "(no summary)"
            print(f"  Issue peek : {issue.get('key', ticket)} — {summary}")


def run_connect(*, github: bool = True, jira: bool = True) -> int:
    """Return 0 if all requested checks succeed, else 1."""
    print("=== ProvePR — Sprint 2 Connect ===")
    failures = 0

    if github:
        try:
            _check_github()
        except ValueError as exc:
            print(f"GitHub FAIL: {exc}")
            failures += 1
        except httpx.HTTPStatusError as exc:
            print(f"GitHub FAIL: HTTP {exc.response.status_code}")
            failures += 1
        except httpx.RequestError as exc:
            print(f"GitHub FAIL: request error ({exc.__class__.__name__})")
            failures += 1

    if jira:
        try:
            _check_jira()
        except ValueError as exc:
            print(f"Jira FAIL: {exc}")
            failures += 1
        except httpx.HTTPStatusError as exc:
            print(f"Jira FAIL: HTTP {exc.response.status_code}")
            failures += 1
        except httpx.RequestError as exc:
            print(f"Jira FAIL: request error ({exc.__class__.__name__})")
            failures += 1

    if failures:
        print("\n=== Sprint 2 FAILED ===")
        print("Fix missing/invalid keys in .env and retry.")
        return 1

    print("\n=== Sprint 2 OK ===")
    print("Working product this sprint: GitHub + Jira connections.")
    print("Security: Jira client is GET-only (no ticket create/edit). Prefer a Browse-only bot account.")
    print("Security: GitHub may post PR comments when reviewing with --post; no code push APIs.")
    print("See SECURITY.md. Next: fetch / review.")
    return 0
