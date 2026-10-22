"""CLI / HTTP: soft ticket quality gate (Story/Bug/Task/Feature; never transitions)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from provepr.config import (
    bug_skip_reporter_emails,
    gate_skip_reporter_names,
    load_env,
    require_jira_settings,
)
from provepr.jira_client import JiraClient
from provepr.jira_text import adf_to_text, build_prd_with_subtasks
from provepr.prd_gate import (
    PrdGateResult,
    evaluate_prd_gate,
    format_prd_gate_jira_adf,
    format_prd_gate_report,
    format_prd_gate_slack,
    prior_gate_comment_exists,
    prior_gate_was_ready,
)
from provepr.prd_gate_ai import maybe_refine_prd_gate_result
from provepr.slack import notify_slack


@dataclass(frozen=True)
class PrdGateRun:
    result: PrdGateResult
    report: str
    jira_comment_url: str | None = None
    slack_detail: str = ""


def _reporter_email(fields: dict) -> str:
    reporter = fields.get("reporter")
    if not isinstance(reporter, dict):
        return ""
    email = reporter.get("emailAddress") or reporter.get("email") or ""
    return str(email).strip()


def _reporter_display_name(fields: dict) -> str:
    reporter = fields.get("reporter")
    if not isinstance(reporter, dict):
        return ""
    return str(reporter.get("displayName") or "").strip()


def _reporter_account_id(fields: dict) -> str:
    reporter = fields.get("reporter")
    if not isinstance(reporter, dict):
        return ""
    return str(reporter.get("accountId") or "").strip()


def _assignee_display_name(fields: dict) -> str:
    assignee = fields.get("assignee")
    if not isinstance(assignee, dict) or not assignee:
        return "Unassigned"
    name = str(assignee.get("displayName") or assignee.get("emailAddress") or "").strip()
    return name or "Unassigned"


def _comment_plain_bodies(comments: list[dict]) -> list[str]:
    bodies: list[str] = []
    for comment in comments:
        body = comment.get("body")
        if isinstance(body, str):
            bodies.append(body)
        else:
            bodies.append(adf_to_text(body))
    return bodies


def execute_prd_gate(
    *,
    ticket: str,
    comment: bool = True,
    notify: bool = True,
    trigger: str = "",
) -> PrdGateRun:
    """
    Score Story / Bug / Task / Feature text (parent + subtasks), optionally comment + Slack.

    Soft only: never transitions the issue (no bounce back to backlog).

    trigger:
      - to_do / "" / manual — normal check
      - in_progress — safety net; no-ops if a prior KodiQA comment already Ready
    """
    key = (ticket or "").strip()
    if not key:
        raise ValueError("--ticket KEY is required")

    trigger_norm = (trigger or "").strip().lower().replace("-", "_")
    reporter_name = ""
    assignee_name = "Unassigned"

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

        prior_ready = False
        prior_comment = False
        if trigger_norm in {"in_progress", "inprogress", "to_do", "todo"}:
            bodies = _comment_plain_bodies(jira.list_comments(key))
            prior_ready = prior_gate_was_ready(bodies)
            prior_comment = prior_gate_comment_exists(bodies)

        prd = build_prd_with_subtasks(issue, subtasks)
        result = evaluate_prd_gate(
            ticket_key=str(issue.get("key") or key),
            issue_type=issue_type or "(unknown)",
            status=status or "(unknown)",
            prd_text=prd,
            subtask_count=len(subtasks),
            reporter_email=_reporter_email(fields),
            reporter_display_name=_reporter_display_name(fields),
            bug_skip_reporter_emails=bug_skip_reporter_emails(),
            skip_reporter_names=gate_skip_reporter_names(),
            trigger=trigger_norm,
            prior_ready=prior_ready,
            prior_comment=prior_comment,
        )
        # Heuristics first (free). Gemini only when gaps + substantial body.
        result = maybe_refine_prd_gate_result(result, prd)
        report = format_prd_gate_report(result)
        reporter_name = _reporter_display_name(fields)
        reporter_account_id = _reporter_account_id(fields)
        assignee_name = _assignee_display_name(fields)

        # Noise control: only publish when there are gaps. Ready / Skipped stay quiet
        # so PMs and creators are not interrupted on already-complete tickets.
        should_publish = (
            not result.skipped and result.verdict == "Needs work"
        )

        comment_url: str | None = None
        if comment and should_publish:
            posted = jira.add_comment(
                result.ticket_key,
                format_prd_gate_jira_adf(
                    result,
                    reporter_account_id=reporter_account_id,
                    reporter_display_name=reporter_name,
                ),
            )
            comment_url = (
                (posted.get("self") if isinstance(posted, dict) else None) or None
            )

    slack_detail = ""
    if notify and not result.skipped and result.verdict == "Needs work":
        slack = notify_slack(
            format_prd_gate_slack(
                result,
                reporter=reporter_name,
                assignee=assignee_name,
            ),
            kind="pm",
        )
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
    trigger: str = "",
) -> int:
    print("=== ProvePR — ticket quality gate (soft) ===")
    load_env()
    try:
        run = execute_prd_gate(
            ticket=ticket, comment=comment, notify=notify, trigger=trigger
        )
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
    elif comment and run.result.skipped:
        print("Jira comment: skipped")
    elif comment and run.result.is_ready:
        print("Jira comment: silent (Ready — no gaps)")
    elif comment:
        print("Jira comment: posted")
    if notify:
        if run.result.skipped:
            print("Slack: skipped")
        elif run.result.is_ready:
            print("Slack: silent (Ready — no gaps)")
        else:
            print(f"Slack: {run.slack_detail or '(no detail)'}")

    if run.result.skipped:
        print("=== Gate skipped ===")
        return 0
    if run.result.is_ready:
        print("=== Gate Ready (silent; status unchanged) ===")
        return 0
    print("=== Gate Needs work (non-blocking; status unchanged) ===")
    return 0
