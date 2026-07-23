"""ProvePR Hermes tool handlers (Jira + GitHub). Safe to unit-test without Hermes."""

from __future__ import annotations

import json
from typing import Any

from provepr.config import require_github_settings, require_jira_settings
from provepr.github_client import GitHubClient
from provepr.jira_client import JiraClient
from provepr.jira_text import issue_prd_text

MAX_PRD_CHARS = 12_000
MAX_DIFF_CHARS = 40_000
MAX_META_CHARS = 4_000


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n...[truncated: kept {limit} of {len(text)} chars]"


def _ok(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True)


def _err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=True)


def get_jira_prd(args: dict, **kwargs: object) -> str:
    """Fetch Jira ticket PRD text for a key like PROV-1."""
    del kwargs
    ticket_key = str(args.get("ticket_key") or "").strip()
    if not ticket_key:
        return _err("ticket_key is required")
    try:
        with JiraClient(require_jira_settings()) as jira:
            issue = jira.get_issue(ticket_key)
        prd = issue_prd_text(issue)
        key = str(issue.get("key") or ticket_key)
        return _ok(
            {
                "ticket_key": key,
                "prd": _truncate(prd or "(empty — no description on ticket)", MAX_PRD_CHARS),
                "prd_chars": len(prd or ""),
            }
        )
    except Exception as exc:  # noqa: BLE001 — tool boundary must not raise
        return _err(f"{exc.__class__.__name__}: {exc}")


def get_pull_request(args: dict, **kwargs: object) -> str:
    """Fetch GitHub PR title/url/body metadata."""
    del kwargs
    repo = str(args.get("repo") or "").strip()
    pr_raw = args.get("pr")
    try:
        pr = int(pr_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _err("pr must be an integer")
    if not repo or "/" not in repo:
        return _err("repo must be owner/name")
    try:
        with GitHubClient(require_github_settings()) as gh:
            pull = gh.get_pull_request(repo, pr)
        meta = {
            "repo": repo,
            "number": pull.get("number"),
            "title": pull.get("title"),
            "html_url": pull.get("html_url"),
            "body": _truncate(str(pull.get("body") or ""), MAX_META_CHARS),
            "head_ref": (pull.get("head") or {}).get("ref"),
            "base_ref": (pull.get("base") or {}).get("ref"),
        }
        return _ok(meta)
    except Exception as exc:  # noqa: BLE001
        return _err(f"{exc.__class__.__name__}: {exc}")


def get_pull_request_diff(args: dict, **kwargs: object) -> str:
    """Fetch unified diff for a GitHub PR."""
    del kwargs
    repo = str(args.get("repo") or "").strip()
    pr_raw = args.get("pr")
    try:
        pr = int(pr_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _err("pr must be an integer")
    if not repo or "/" not in repo:
        return _err("repo must be owner/name")
    try:
        with GitHubClient(require_github_settings()) as gh:
            diff = gh.get_pull_request_diff(repo, pr)
        truncated = _truncate(diff or "(empty)", MAX_DIFF_CHARS)
        return _ok(
            {
                "repo": repo,
                "pr": pr,
                "diff": truncated,
                "diff_chars": len(diff or ""),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(f"{exc.__class__.__name__}: {exc}")


SCHEMA_GET_JIRA_PRD = {
    "name": "get_jira_prd",
    "description": (
        "Fetch the Jira ticket summary+description (PRD text) for a ticket key. "
        "Call this before writing the requirements coverage section."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "ticket_key": {
                "type": "string",
                "description": "Jira issue key, e.g. PROV-1 or SX-2869",
            },
        },
        "required": ["ticket_key"],
    },
}

SCHEMA_GET_PULL_REQUEST = {
    "name": "get_pull_request",
    "description": (
        "Fetch GitHub pull request metadata (title, url, body, branch refs). "
        "Use with owner/name repo and PR number."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "GitHub repository as owner/name",
            },
            "pr": {
                "type": "integer",
                "description": "Pull request number",
            },
        },
        "required": ["repo", "pr"],
    },
}

SCHEMA_GET_PULL_REQUEST_DIFF = {
    "name": "get_pull_request_diff",
    "description": (
        "Fetch the unified diff for a GitHub pull request. "
        "Use this as the primary evidence of what the PR changes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "repo": {
                "type": "string",
                "description": "GitHub repository as owner/name",
            },
            "pr": {
                "type": "integer",
                "description": "Pull request number",
            },
        },
        "required": ["repo", "pr"],
    },
}
