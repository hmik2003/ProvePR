"""Shared helpers for PR hook / skip-notify HTTP handlers."""

from __future__ import annotations

from dataclasses import dataclass

from provepr.jira_key import extract_jira_key, primary_jira_key_from_title


@dataclass(frozen=True)
class PrTicketDecision:
    action: str  # review | skip
    ticket: str = ""
    skip_reason: str = ""  # none | multiple
    skip_detail: str = ""
    source: str = ""  # title | fallback | ""


def decide_pr_ticket(
    *,
    title: str = "",
    branch: str = "",
    body: str = "",
) -> PrTicketDecision:
    """Apply 1-ticket-in-title policy; branch/body only if title has no key."""
    primary, title_keys = primary_jira_key_from_title(title)
    if len(title_keys) > 1:
        return PrTicketDecision(
            action="skip",
            skip_reason="multiple",
            skip_detail=",".join(title_keys),
            source="title",
        )
    if primary:
        return PrTicketDecision(
            action="review",
            ticket=primary,
            source="title",
        )
    fallback = extract_jira_key(None, branch, body) or ""
    if fallback:
        return PrTicketDecision(
            action="review",
            ticket=fallback,
            source="fallback",
        )
    return PrTicketDecision(
        action="skip",
        skip_reason="none",
        source="",
    )
