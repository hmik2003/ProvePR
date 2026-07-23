"""Hermes Agent review engine (Option 2: tool-using loop + Gemini)."""

from __future__ import annotations

import os
from typing import Any

from provepr.config import GeminiSettings
from provepr.hermes_tools import (
    SCHEMA_GET_JIRA_PRD,
    SCHEMA_GET_PULL_REQUEST,
    SCHEMA_GET_PULL_REQUEST_DIFF,
    get_jira_prd,
    get_pull_request,
    get_pull_request_diff,
)

GEMINI_NATIVE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MAX_HERMES_ITERATIONS = 8
PROVEPR_TOOLSET = "provepr"

_TOOLS_REGISTERED = False


class HermesUnavailableError(RuntimeError):
    """Raised when hermes-agent cannot be imported or started."""


def hermes_available() -> bool:
    try:
        from run_agent import AIAgent  # noqa: F401

        return True
    except ImportError:
        return False


def register_provepr_tools(*, force: bool = False) -> None:
    """Register ProvePR tools on the Hermes global registry (idempotent)."""
    global _TOOLS_REGISTERED
    if _TOOLS_REGISTERED and not force:
        return
    try:
        from tools.registry import registry
    except ImportError as exc:
        raise HermesUnavailableError(
            "hermes-agent is not installed (need Python 3.11-3.13 + pip install)"
        ) from exc

    specs = [
        ("get_jira_prd", SCHEMA_GET_JIRA_PRD, get_jira_prd, "Fetch Jira PRD text"),
        (
            "get_pull_request",
            SCHEMA_GET_PULL_REQUEST,
            get_pull_request,
            "Fetch GitHub PR metadata",
        ),
        (
            "get_pull_request_diff",
            SCHEMA_GET_PULL_REQUEST_DIFF,
            get_pull_request_diff,
            "Fetch GitHub PR unified diff",
        ),
    ]
    for name, schema, handler, description in specs:
        registry.register(
            name=name,
            toolset=PROVEPR_TOOLSET,
            schema=schema,
            handler=handler,
            check_fn=None,
            requires_env=[],
            description=description,
            override=True,
        )
    _TOOLS_REGISTERED = True


def build_hermes_user_message(
    *,
    repo: str,
    pr: int,
    ticket_key: str,
) -> str:
    return f"""Review this pull request against its Jira ticket using your ProvePR tools.

Targets:
- GitHub repo: {repo}
- PR number: {pr}
- Jira ticket: {ticket_key}

Required workflow:
1. Call get_jira_prd with ticket_key={ticket_key}
2. Call get_pull_request with repo={repo} and pr={pr}
3. Call get_pull_request_diff with repo={repo} and pr={pr}
4. Produce the structured ProvePR review from the tool results only.
   Do not invent files or behavior not evidenced in the diff/PRD.

Required output format (be thorough; use markdown):
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


def run_hermes_review(
    *,
    repo: str,
    pr: int,
    ticket_key: str,
    gemini: GeminiSettings,
    system_prompt: str,
) -> str:
    """
    Run a cost-capped Hermes tool loop (max MAX_HERMES_ITERATIONS model turns).
    Raises HermesUnavailableError if hermes-agent is missing.
    """
    try:
        from run_agent import AIAgent
    except ImportError as exc:
        raise HermesUnavailableError(
            "hermes-agent is not installed (Docker/Python 3.12 recommended)"
        ) from exc

    register_provepr_tools()

    # Prefer project plugin discovery when present (optional complement to registry).
    os.environ.setdefault("HERMES_ENABLE_PROJECT_PLUGINS", "1")
    try:
        from hermes_cli.plugins import discover_plugins

        discover_plugins()
    except Exception:
        pass

    agent_kwargs: dict[str, Any] = {
        "model": gemini.model,
        "provider": "gemini",
        "api_key": gemini.api_key,
        "base_url": GEMINI_NATIVE_BASE_URL,
        "enabled_toolsets": [PROVEPR_TOOLSET],
        "max_iterations": MAX_HERMES_ITERATIONS,
        "quiet_mode": True,
        "skip_memory": True,
        "skip_context_files": True,
        "ephemeral_system_prompt": system_prompt,
        "save_trajectories": False,
    }

    agent = AIAgent(**agent_kwargs)
    user_message = build_hermes_user_message(
        repo=repo, pr=pr, ticket_key=ticket_key
    )

    if hasattr(agent, "run_conversation"):
        result = agent.run_conversation(user_message=user_message)
        if isinstance(result, dict):
            text = (
                result.get("final_response")
                or result.get("response")
                or result.get("content")
                or ""
            )
            if text:
                return str(text).strip()
        if isinstance(result, str) and result.strip():
            return result.strip()

    if hasattr(agent, "chat"):
        text = agent.chat(user_message)
        if text and str(text).strip():
            return str(text).strip()

    raise ValueError("Hermes returned an empty review")
