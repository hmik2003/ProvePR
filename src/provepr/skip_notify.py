"""Notify QA when ProvePR skips a PR review (no Gemini spend)."""

from __future__ import annotations

import httpx

from provepr.config import load_env, require_github_settings
from provepr.github_client import GitHubClient
from provepr.slack import notify_slack

REASON_NONE = "none"
REASON_MULTIPLE = "multiple"


def format_skip_message(
    *,
    repo: str,
    pr: int,
    reason: str,
    title: str = "",
    pr_url: str = "",
    detail: str = "",
) -> str:
    """Slack / log text for a skipped review."""
    if reason == REASON_MULTIPLE:
        why = (
            "PR title has multiple Jira keys "
            f"({detail or '2+'}). Company policy is 1 ticket per PR."
        )
        ask = "Ask the author to keep exactly one key in the title (split the work if needed)."
    else:
        why = "No Jira ticket key found in PR title, branch, or body."
        ask = (
            "Please check whether this PR should map to a ticket, "
            "or ask the author to add `PROJ-123:` to the title."
        )

    lines = [
        "ProvePR skipped review (saved Gemini spend)",
        "",
        f"Repo: {repo}#{pr}",
    ]
    if title:
        lines.append(f"Title: {title}")
    lines.append(f"Reason: {why}")
    lines.append(f"QA follow-up: {ask}")
    if pr_url:
        lines.append(f"PR: {pr_url}")
    return "\n".join(lines)


def format_skip_pr_comment(
    *,
    reason: str,
    detail: str = "",
) -> str:
    """Short GitHub PR comment — no AI, paper trail only."""
    if reason == REASON_MULTIPLE:
        body_why = (
            f"Title contains multiple Jira keys (`{detail or '2+'}`). "
            "Company policy is **1 ticket ↔ 1 PR**."
        )
        fix = "Keep exactly one key in the title, then push / re-open."
    else:
        body_why = "No Jira ticket key found in the PR title, branch, or body."
        fix = "Add a key like `PROV-10: …` to the title, then push / re-open."

    return (
        "## ProvePR skipped\n\n"
        f"{body_why}\n\n"
        "Review was **not** run (no Gemini spend). "
        "QA has been notified to look into it.\n\n"
        f"**Fix:** {fix}\n"
    )


def run_skip_notify(
    *,
    repo: str,
    pr: int,
    reason: str = REASON_NONE,
    title: str = "",
    pr_url: str = "",
    detail: str = "",
    comment: bool = True,
) -> int:
    """
    Slack DM (or stub) when review is skipped. Optionally comment on the PR.
    Always exit 0 on stub so CI stays green; real Slack/GitHub errors still fail.
    """
    print("=== ProvePR — skip notify (no Gemini) ===")
    load_env()
    repo = (repo or "").strip()
    if not repo or "/" not in repo:
        print("Skip notify FAIL: --repo owner/name is required")
        return 1
    if pr < 1:
        print("Skip notify FAIL: --pr must be a positive integer")
        return 1

    reason_norm = (reason or REASON_NONE).strip().lower()
    if reason_norm not in {REASON_NONE, REASON_MULTIPLE}:
        reason_norm = REASON_NONE

    message = format_skip_message(
        repo=repo,
        pr=pr,
        reason=reason_norm,
        title=title,
        pr_url=pr_url,
        detail=detail,
    )
    print(message)

    try:
        slack = notify_slack(message)
        print(f"Slack: {slack.detail}")
    except httpx.HTTPStatusError as exc:
        print(f"Slack FAIL: HTTP {exc.response.status_code}")
        return 1
    except httpx.RequestError as exc:
        print(f"Slack FAIL: request error ({exc.__class__.__name__})")
        return 1
    except ValueError as exc:
        print(f"Slack FAIL: {exc}")
        return 1

    if comment:
        body = format_skip_pr_comment(reason=reason_norm, detail=detail)
        try:
            with GitHubClient(require_github_settings()) as gh:
                posted = gh.create_issue_comment(repo, pr, body)
            print(f"GitHub: skip comment → {posted.get('html_url') or '(no url)'}")
        except ValueError as exc:
            print(f"GitHub FAIL: {exc}")
            return 1
        except httpx.HTTPStatusError as exc:
            print(f"GitHub FAIL: HTTP {exc.response.status_code}")
            return 1
        except httpx.RequestError as exc:
            print(f"GitHub FAIL: request error ({exc.__class__.__name__})")
            return 1

    print("=== Skip notify OK ===")
    return 0
