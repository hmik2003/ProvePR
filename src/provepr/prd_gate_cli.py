"""CLI / HTTP: soft PRD quality gate for Stories (comment + Slack; never transitions)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from provepr.config import load_env, require_jira_settings
from provepr.jira_client import JiraClient
from provepr.jira_text import build_prd_with_subtasks
from provepr.prd_gate import (
    PrdGateResult,
    evaluate_prd_gate,
    format_prd_gate_jira_adf,
    format_prd_gate_report,
    format_prd_gate_slack,
)
from provepr.slack import notify_slack


@dataclass(frozen=True)
class PrdGateRun:
    result: PrdGateResult
    report: str
    jira_comment_url: str | None = None
    slack_detail: str = ""


def execute_prd_gate(
    *,
    ticket: str,
    comment: bool = True,
    notify: bool = True,
) -> PrdGateRun:
    """
    Score a Story PRD (parent + subtasks), optionally comment on Jira + Slack QA.

    Soft only: never transitions the issue (no bounce back to backlog).
    """
    key = (ticket or "").strip()
    if not key:
        raise ValueError("--ticket KEY is required")

    with JiraClient(require_jira_settings()) as jira:
        issue = jira.get_issue(key)
        subtasks = jira.get_subtasks(key)

        fields = issue.get("fields") or {}
        issue_type = ""
        it = fields.get("issuetype")
        if isinstance(it, dict):
            issue_type = str(it.get("name") or "")
        status = ""
        st = fields.get("status")
        if isinstance(st, dict):
            status = str(st.get("name") or "")

        prd = build_prd_with_subtasks(issue, subtasks)
        result = evaluate_prd_gate(
            ticket_key=str(issue.get("key") or key),
            issue_type=issue_type or "(unknown)",
            status=status or "(unknown)",
            prd_text=prd,
            subtask_count=len(subtasks),
        )
        report = format_prd_gate_report(result)

        comment_url: str | None = None
        # Comment on Stories only (Ready or Needs work) — skip Bugs/Tasks.
        if comment and not result.skipped:
            posted = jira.add_comment(
                result.ticket_key, format_prd_gate_jira_adf(result)
            )
            comment_url = (
                (posted.get("self") if isinstance(posted, dict) else None) or None
            )

    slack_detail = ""
    if notify and not result.skipped:
        slack = notify_slack(format_prd_gate_slack(result))
        slack_detail = slack.detail

    return PrdGateRun(
        result=result,
        report=report,
        jira_comment_url=comment_url,
        slack_detail=slack_detail,
    )


def run_prd_gate(
    *,
    ticket: str,
    notify: bool = True,
    comment: bool = True,
) -> int:
    print("=== ProvePR — PRD quality gate (soft) ===")
    load_env()
    try:
        run = execute_prd_gate(ticket=ticket, comment=comment, notify=notify)
    except ValueError as exc:
        print(f"PRD gate FAIL: {exc}")
        return 1
    except httpx.HTTPStatusError as exc:
        print(f"PRD gate FAIL: HTTP {exc.response.status_code}")
        detail = (exc.response.text or "")[:300]
        if detail:
            print(f"  {detail}")
        return 1
    except httpx.RequestError as exc:
        print(f"PRD gate FAIL: request error ({exc.__class__.__name__})")
        return 1

    print()
    print(run.report)
    if run.jira_comment_url:
        print(f"Jira comment: posted ({run.jira_comment_url})")
    elif comment and not run.result.skipped:
        print("Jira comment: posted")
    if notify:
        if run.result.skipped:
            print("Slack: skipped (non-Story)")
        else:
            print(f"Slack: {run.slack_detail or '(no detail)'}")

    if run.result.skipped:
        print("=== PRD gate skipped (not a Story) ===")
        return 0
    if run.result.is_ready:
        print("=== PRD gate Ready (ticket stays in To Do) ===")
        return 0
    print("=== PRD gate Needs work (non-blocking; ticket stays in To Do) ===")
    return 0
