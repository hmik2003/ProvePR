"""Sprint 4/5/Hermes review — Hermes tool loop (preferred) or single-shot Gemini fallback."""

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
from provepr.hermes_review import (
    MAX_HERMES_ITERATIONS,
    HermesUnavailableError,
    hermes_available,
    run_hermes_review,
)
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
    """Single-shot fallback prompt (used when Hermes is unavailable)."""
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
0. **TL;DR** (devs read this first — keep under 6 lines):
   - **Verdict:** one of Requirements largely met | Partial | Insufficient evidence
   - **Must-fix:** 0-3 bullets (Blocker/Major only; write "None" if none)
   - **QA should still verify:** 1-3 concrete checks
1. **PRD quality assessment:** Rich | Medium | Vague/Empty — 2-4 sentences on how ticket quality limits this review
2. **Verdict:** Requirements largely met | Partial | Insufficient evidence
3. **AC coverage table:** For each stated criterion (or inferred theme if vague):
   - Criterion text
   - Status: Covered / Partial / Missing / Unclear
   - Evidence: file/hunk note OR why unclear
4. **Findings:** severity (Blocker / Major / Minor / Info) + detail + file/area if known
   Put Blocker/Major first. Include at least one finding when the PRD is vague (usually about missing AC).
5. **Risk & edge cases:** what could break in staging based on the diff + PRD gaps
6. **Suggested human SQA focus:** concrete manual/API checks a tester should still run (numbered steps preferred)
7. **Open questions:** for author / product (especially when PRD is thin)
8. **Summary for Slack:** one short paragraph a busy lead can read in 10 seconds
"""


def format_pr_comment(*, ticket_key: str, model: str, review_text: str) -> str:
    return (
        "## ProvePR review\n\n"
        f"**Ticket:** `{ticket_key}`  \n"
        f"**Engine:** `{model}`  \n"
        "_Static requirements-vs-diff review (not a runtime / E2E test). "
        "Start with **TL;DR**; treat Blocker/Major as must-fix before merge._\n\n"
        "---\n\n"
        f"{review_text.strip()}\n"
    )


def _run_single_shot_gemini(
    *,
    full_name: str,
    pr_number: int,
    ticket_key: str,
    gemini,
) -> tuple[str, str]:
    """Return (review_text, engine_label). Prefetch PRD+diff then one Gemini call."""
    gh_settings = require_github_settings()
    with GitHubClient(gh_settings) as gh:
        pull = gh.get_pull_request(full_name, pr_number)
        diff = gh.get_pull_request_diff(full_name, pr_number)
    with JiraClient(require_jira_settings()) as jira:
        issue = jira.get_issue(ticket_key)
    prd = issue_prd_text(issue)
    resolved_ticket = str(issue.get("key") or ticket_key)

    prd_t, prd_cut = _truncate("PRD", prd, MAX_PRD_CHARS)
    diff_t, diff_cut = _truncate("diff", diff, MAX_DIFF_CHARS)
    print(f"Input   : PRD {len(prd_t)} chars" + (" (truncated)" if prd_cut else ""))
    print(f"Input   : diff {len(diff_t)} chars" + (" (truncated)" if diff_cut else ""))
    print("Calling Gemini once (single-shot fallback)...")

    user_prompt = build_user_prompt(
        pr_title=str(pull.get("title") or ""),
        pr_url=str(pull.get("html_url") or ""),
        ticket_key=resolved_ticket,
        prd=prd,
        diff=diff,
    )
    with GeminiClient(gemini) as client:
        review_text = client.generate_text(system=SYSTEM_PROMPT, user=user_prompt)
    return review_text, f"single-shot Gemini / {gemini.model}"


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
        print("Review FAIL: --post requires --yes (Gemini spend + publish)")
        return 1

    try:
        full_name, pr_number, ticket_key = resolve_targets(
            repo=repo, pr=pr, ticket=ticket
        )
        gemini = require_gemini_settings()
    except ValueError as exc:
        print(f"Review FAIL: {exc}")
        return 1

    use_hermes = hermes_available()
    print(f"Targets : {full_name}#{pr_number} <-> {ticket_key}")
    print(f"Model   : {gemini.model}")
    if use_hermes:
        print(
            f"Engine  : Hermes Agent + Gemini "
            f"(up to {MAX_HERMES_ITERATIONS} model turns; ProvePR tools only)"
        )
    else:
        print(
            "Engine  : single-shot Gemini fallback "
            "(hermes-agent not installed — use Python 3.12 Docker image)"
        )
    if post:
        print("Publish : GitHub PR comment + Slack (or stub)")

    if not yes:
        print("\nDry-run only — no Gemini spend.")
        print("Re-run with --yes to review, or --yes --post to review and publish.")
        return 0

    engine_label = f"Hermes + {gemini.model}"
    review_text = ""

    try:
        if use_hermes:
            print("Starting Hermes tool loop...")
            # Ensure GitHub/Jira settings exist before tool calls.
            require_github_settings()
            require_jira_settings()
            review_text = run_hermes_review(
                repo=full_name,
                pr=pr_number,
                ticket_key=ticket_key,
                gemini=gemini,
                system_prompt=SYSTEM_PROMPT,
            )
        else:
            review_text, engine_label = _run_single_shot_gemini(
                full_name=full_name,
                pr_number=pr_number,
                ticket_key=ticket_key,
                gemini=gemini,
            )
    except HermesUnavailableError as exc:
        print(f"Hermes unavailable ({exc}); falling back to single-shot Gemini...")
        try:
            review_text, engine_label = _run_single_shot_gemini(
                full_name=full_name,
                pr_number=pr_number,
                ticket_key=ticket_key,
                gemini=gemini,
            )
        except httpx.HTTPStatusError as http_exc:
            detail = ""
            try:
                detail = http_exc.response.json().get("error", {}).get("message", "")
            except Exception:
                detail = (http_exc.response.text or "")[:200]
            print(f"Review FAIL: Gemini HTTP {http_exc.response.status_code}")
            if detail:
                print(f"  {detail}")
            return 1
        except (httpx.RequestError, ValueError) as fallback_exc:
            print(f"Review FAIL: {fallback_exc}")
            return 1
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("error", {}).get("message", "")
        except Exception:
            detail = (exc.response.text or "")[:200]
        print(f"Review FAIL: HTTP {exc.response.status_code} during review")
        if detail:
            print(f"  {detail}")
        return 1
    except (httpx.RequestError, ValueError) as exc:
        print(f"Review FAIL: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — surface Hermes runtime errors cleanly
        print(f"Review FAIL: {exc.__class__.__name__}: {exc}")
        return 1

    print("\n--- AI review ---")
    _safe_print(review_text)

    if post:
        comment_body = format_pr_comment(
            ticket_key=ticket_key,
            model=engine_label,
            review_text=review_text,
        )
        try:
            gh_settings = require_github_settings()
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
            f"ProvePR review on {full_name}#{pr_number} ({ticket_key})\n"
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

        print("\n=== Review published OK ===")
        print("Working product: Hermes/Gemini review + GitHub PR comment (+ Slack).")
        return 0

    print("\n=== Review OK ===")
    print(f"Working product: {engine_label} PRD-vs-diff review.")
    print("Add --post to publish the comment.")
    return 0
