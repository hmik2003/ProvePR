"""CLI: python -m provepr prd-gate — soft PRD quality check for Stories."""

from __future__ import annotations

import httpx

from provepr.config import load_env, require_jira_settings
from provepr.jira_client import JiraClient
from provepr.jira_text import build_prd_with_subtasks
from provepr.prd_gate import evaluate_prd_gate, format_prd_gate_report
from provepr.slack import notify_slack


def run_prd_gate(*, ticket: str, notify: bool = False) -> int:
    print("=== ProvePR — PRD quality gate (soft) ===")
    load_env()
    key = (ticket or "").strip()
    if not key:
        print("PRD gate FAIL: --ticket KEY is required")
        return 1

    try:
        with JiraClient(require_jira_settings()) as jira:
            issue = jira.get_issue(key)
            subtasks = jira.get_subtasks(key)
    except ValueError as exc:
        print(f"PRD gate FAIL: {exc}")
        return 1
    except httpx.HTTPStatusError as exc:
        print(f"PRD gate FAIL: HTTP {exc.response.status_code}")
        return 1
    except httpx.RequestError as exc:
        print(f"PRD gate FAIL: request error ({exc.__class__.__name__})")
        return 1

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
    print()
    print(report)

    if notify:
        try:
            slack = notify_slack(report)
            print(f"Slack: {slack.detail}")
        except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
            print(f"Slack FAIL: {exc}")
            return 1

    if result.skipped:
        print("=== PRD gate skipped (not a Story) ===")
        return 0
    if result.is_ready:
        print("=== PRD gate Ready ===")
        return 0
    print("=== PRD gate Needs work (non-blocking) ===")
    return 0  # soft: never fail CI for thin PRDs yet
