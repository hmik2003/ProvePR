"""Sprint 4 review — single-shot Gemini PRD vs diff review (cost-guarded)."""

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

MAX_PRD_CHARS = 12_000
MAX_DIFF_CHARS = 40_000

SYSTEM_PROMPT = """You are ProvePR, an SQA-style PR reviewer.
Compare the Jira requirements (PRD) to the GitHub PR diff only.
Do not invent files or behavior that are not evidenced in the diff.
Be concise. Use the exact output structure requested.
This is a static review, not a guarantee the feature works in staging.
Prefer ASCII punctuation (use -> instead of arrows) so terminals stay compatible.
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
{prd_t or "(empty)"}

## PR diff
{diff_t or "(empty)"}

## Required output format
1. **Verdict:** Requirements largely met | Partial | Insufficient evidence
2. **AC coverage:** bullet list of criteria → Covered / Partial / Missing / Unclear
3. **Findings:** severity (Blocker / Major / Minor / Info) + short note + file if known
4. **Suggested human SQA focus:** what to still verify manually / in staging
5. **Open questions:** ambiguities for author / product
"""


def run_review(
    *,
    repo: str | None = None,
    pr: int | None = None,
    ticket: str | None = None,
    yes: bool = False,
) -> int:
    print("=== ProvePR — Sprint 4 Review (cost-guarded) ===")
    load_env()
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

    if not yes:
        print("\nDry-run only — no Gemini spend.")
        print("Re-run with --yes to perform the single review call.")
        print("Example: python -m provepr review --yes")
        return 0

    try:
        with GitHubClient(require_github_settings()) as gh:
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

    user_prompt = build_user_prompt(
        pr_title=str(pull.get("title") or ""),
        pr_url=str(pull.get("html_url") or ""),
        ticket_key=str(issue.get("key") or ticket_key),
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
    print("\n=== Sprint 4 OK ===")
    print("Working product: single-shot Gemini PRD-vs-diff review (Hermes loop deferred for budget).")
    return 0
