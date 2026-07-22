"""Optional Slack Incoming Webhook notify (stub if unset)."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from provepr.config import load_env


@dataclass(frozen=True)
class SlackResult:
    posted: bool
    detail: str


def notify_slack(text: str) -> SlackResult:
    """Post to Slack webhook if SLACK_WEBHOOK_URL is set; otherwise stub."""
    load_env()
    url = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
    if not url:
        return SlackResult(
            posted=False,
            detail="Slack stub: skipped (set SLACK_WEBHOOK_URL to enable)",
        )

    response = httpx.post(url, json={"text": text}, timeout=30.0)
    response.raise_for_status()
    return SlackResult(posted=True, detail="Slack OK: webhook delivered")
