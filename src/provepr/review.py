"""Sprint 4/5 review — single-shot Gemini review + optional GitHub/Slack publish."""

from __future__ import annotations

import sys

import httpx

from provepr.config import (
    load_env,
    require_gemini_settings,
    require_github_settings,
    require_jira_settings,
)
from provepr.fetch import resolve_targets
from provepr.gemini_client import GeminiClient
from provepr.github_client import GitHubClient
from provepr.jira_client import JiraClient
from provepr.jira_text import issue_prd_text
from provepr.slack import notify_slack

MAX_PRD_CHARS = 12_000
MAX_DIFF_CHARS = 40_000

SYSTEM_PROMPT = """You are ProvePR, a senior SQA-style PR reviewer.
Compare the Jira requirements (PRD) to the GitHub PR diff only.
Do not invent files or behavior that are not evidenced in the diff.
Prefer ASCII punctuation (use -> instead of arrows) so terminals stay compatible.
This is a static review, not a runtime/E2E guarantee.

Ticket quality varies. Adapt explicitly:
- If the PRD is rich (AC, steps, expected/actual): map each AC and call out gaps precisely.
- If the PRD is medium (Context/Scope/Done when): treat Done-when bullets as AC.
- If the PRD is vague or nearly empty: do NOT pretend AC exist. Mark coverage Unclear,
  infer only cautious risks from the diff, and list what the ticket should have said.
Always produce a detailed, structured report using the required sections.
"""


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def _truncate(label: str, text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + f"\n\n...[truncated {label}: kept {limit} of {len(text)} chars]", True


def build_user_prompt(
    *,
    pr_title: str,
    pr_url: str,
    ticket_key: str,
    prd: str,
    diff: str,
) -> str:
    prd_t, _ = _truncate("PRD", prd, MAX_PRD_CHARS)
    diff_t, _ = _truncate("diff", diff, MAX_DIFF_CHARS)
    return f"""## GitHub PR
Title: {pr_title}
URL: {pr_url}

## Jira ticket
Key: {ticket_key}

## Requirements / PRD
{prd_t or "(empty — no description on ticket)"}

## PR diff
{diff_t or "(empty)"}

## Required output format (be thorough; use markdown)
1. **PRD quality assessment:** Rich | Medium | Vague/Empty — 2-4 sentences on how ticket quality limits this review
2. **Verdict:** Requirements largely met | Partial | Insufficient evidence
3. **AC coverage table:** For each stated criterion (or inferred theme if vague):
   - Criterion text
   - Status: Covered / Partial / Missing / Unclear
   - Evidence: file/hunk note OR why unclear
4. **Findings:** severity (Blocker / Major / Minor / Info) + detail + file/area if known
   Include at least one finding when the PRD is vague (usually about missing AC).
5. **Risk & edge cases:** what could break in staging based on the diff + PRD gaps
6. **Suggested human SQA focus:** concrete manual/API checks a tester should still run
7. **Open questions:** for author / product (especially when PRD is thin)
8. **Summary for Slack:** one short paragraph a busy lead can read in 10 seconds
"""


def format_pr_comment(*, ticket_key: str, model: str, review_text: str) -> str:
    return (
        "## ProvePR review\n\n"
        f"**Ticket:** `{ticket_key}`  \n"
        f"**Model:** `{model}`  \n"
        "_Static requirements-vs-diff review (not a runtime test)._\n\n"
        "---\n\n"
        f"{review_text.strip()}\n"
    )


def run_review(
    *,
    repo: str | None = None,
    pr: int | None = None,
    ticket: str | None = None,
    yes: bool = False,
    post: bool = False,
) -> int:
    print("=== ProvePR — Review (cost-guarded) ===")
    load_env()

    if post and not yes:
        print("Review FAIL: --post requires --yes (one Gemini call + publish)")
        return 1

    try:
        full_name, pr_number, ticket_key = resolve_targets(
            repo=repo, pr=pr, ticket=ticket
        )
        gemini = require_gemini_settings()
    except ValueError as exc:
        print(f"Review FAIL: {exc}")
        return 1

    print(f"Targets : {full_name}#{pr_number} <-> {ticket_key}")
    print(f"Model   : {gemini.model}")
    print("Cost    : exactly ONE Gemini call when --yes is passed (no retries)")
    if post:
        print("Publish : GitHub PR comment + Slack (or stub)")

    if not yes:
        print("\nDry-run only — no Gemini spend.")
        print("Re-run with --yes to review, or --yes --post to review and publish.")
        return 0

    try:
        gh_settings = require_github_settings()
        with GitHubClient(gh_settings) as gh:
            pull = gh.get_pull_request(full_name, pr_number)
            diff = gh.get_pull_request_diff(full_name, pr_number)
        with JiraClient(require_jira_settings()) as jira:
            issue = jira.get_issue(ticket_key)
        prd = issue_prd_text(issue)
    except httpx.HTTPStatusError as exc:
        print(f"Review FAIL: HTTP {exc.response.status_code} fetching inputs")
        return 1
    except httpx.RequestError as exc:
        print(f"Review FAIL: request error fetching inputs ({exc.__class__.__name__})")
        return 1

    prd_t, prd_cut = _truncate("PRD", prd, MAX_PRD_CHARS)
    diff_t, diff_cut = _truncate("diff", diff, MAX_DIFF_CHARS)
    print(f"Input   : PRD {len(prd_t)} chars" + (" (truncated)" if prd_cut else ""))
    print(f"Input   : diff {len(diff_t)} chars" + (" (truncated)" if diff_cut else ""))
    print("Calling Gemini once...")

    resolved_ticket = str(issue.get("key") or ticket_key)
    user_prompt = build_user_prompt(
        pr_title=str(pull.get("title") or ""),
        pr_url=str(pull.get("html_url") or ""),
        ticket_key=resolved_ticket,
        prd=prd,
        diff=diff,
    )

    try:
        with GeminiClient(gemini) as client:
            review_text = client.generate_text(system=SYSTEM_PROMPT, user=user_prompt)
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = (exc.response.text or "")[:200]
        print(f"Review FAIL: Gemini HTTP {exc.response.status_code}")
        if detail:
            print(f"  {detail}")
        return 1
    except (httpx.RequestError, ValueError) as exc:
        print(f"Review FAIL: {exc}")
        return 1

    print("\n--- AI review ---")
    _safe_print(review_text)

    if post:
        comment_body = format_pr_comment(
            ticket_key=resolved_ticket,
            model=gemini.model,
            review_text=review_text,
        )
        try:
            with GitHubClient(gh_settings) as gh:
                comment = gh.create_issue_comment(full_name, pr_number, comment_body)
            comment_url = comment.get("html_url") or "(no url)"
            print(f"\nGitHub  : comment posted → {comment_url}")
        except httpx.HTTPStatusError as exc:
            print(f"\nGitHub FAIL: HTTP {exc.response.status_code} posting comment")
            return 1
        except httpx.RequestError as exc:
            print(f"\nGitHub FAIL: request error ({exc.__class__.__name__})")
            return 1

        slack_text = (
            f"ProvePR review on {full_name}#{pr_number} ({resolved_ticket})\n"
            f"{comment_url}"
        )
        try:
            slack = notify_slack(slack_text)
            print(f"Slack   : {slack.detail}")
        except httpx.HTTPStatusError as exc:
            print(f"Slack FAIL: HTTP {exc.response.status_code}")
            return 1
        except httpx.RequestError as exc:
            print(f"Slack FAIL: request error ({exc.__class__.__name__})")
            return 1
        except ValueError as exc:
            print(f"Slack FAIL: {exc}")
            return 1

        print("\n=== Sprint 5 OK ===")
        print("Working product: review + GitHub PR comment (+ Slack or stub).")
        return 0

    print("\n=== Sprint 4 OK ===")
    print("Working product: single-shot Gemini PRD-vs-diff review.")
    print("Add --post to publish the comment (Sprint 5).")
    return 0
