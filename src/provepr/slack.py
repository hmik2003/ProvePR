"""Slack notify — Dev vs PM bots (DM); shared token fallback; webhook optional."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx

from provepr.config import load_env

SLACK_API = "https://slack.com/api"

SlackKind = Literal["dev", "pm"]


@dataclass(frozen=True)
class SlackResult:
    posted: bool
    detail: str


def _token_for_kind(kind: SlackKind) -> str:
    """Prefer kind-specific bot; fall back to legacy SLACK_BOT_TOKEN."""
    if kind == "pm":
        specific = (os.getenv("SLACK_PM_BOT_TOKEN") or "").strip()
    else:
        specific = (os.getenv("SLACK_DEV_BOT_TOKEN") or "").strip()
    if specific:
        return specific
    return (os.getenv("SLACK_BOT_TOKEN") or "").strip()


def notify_slack(text: str, *, kind: SlackKind = "dev") -> SlackResult:
    """
    Notify order:
    1) Bot token for `kind` (or legacy SLACK_BOT_TOKEN) + SLACK_DM_USER_ID → DM
    2) SLACK_WEBHOOK_URL → Incoming Webhook (channel; legacy; ignores kind)
    3) else stub

    kind:
      - dev → PR reviews + skip-notify (SLACK_DEV_BOT_TOKEN)
      - pm  → ticket quality gates (SLACK_PM_BOT_TOKEN)
    """
    load_env()
    bot_token = _token_for_kind(kind)
    dm_user = (os.getenv("SLACK_DM_USER_ID") or "").strip()
    webhook = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()

    if bot_token and dm_user:
        result = _dm_via_bot(bot_token=bot_token, user_id=dm_user, text=text)
        if result.posted:
            return SlackResult(
                posted=True,
                detail=f"{result.detail} ({kind})",
            )
        return result

    if bot_token and not dm_user:
        return SlackResult(
            posted=False,
            detail=(
                f"Slack stub ({kind}): bot token set but SLACK_DM_USER_ID missing"
            ),
        )

    if webhook:
        response = httpx.post(webhook, json={"text": text}, timeout=30.0)
        response.raise_for_status()
        return SlackResult(posted=True, detail="Slack OK: webhook delivered")

    return SlackResult(
        posted=False,
        detail=(
            f"Slack stub ({kind}): skipped "
            "(set SLACK_DEV_BOT_TOKEN / SLACK_PM_BOT_TOKEN or SLACK_BOT_TOKEN "
            "+ SLACK_DM_USER_ID)"
        ),
    )


def _dm_via_bot(*, bot_token: str, user_id: str, text: str) -> SlackResult:
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    with httpx.Client(base_url=SLACK_API, headers=headers, timeout=30.0) as client:
        opened = client.post("/conversations.open", json={"users": user_id})
        opened.raise_for_status()
        open_data = opened.json()
        if not open_data.get("ok"):
            err = open_data.get("error") or "conversations.open failed"
            raise ValueError(f"Slack API error: {err}")
        channel = (open_data.get("channel") or {}).get("id")
        if not channel:
            raise ValueError("Slack conversations.open returned no channel id")

        posted = client.post(
            "/chat.postMessage",
            json={"channel": channel, "text": text},
        )
        posted.raise_for_status()
        post_data = posted.json()
        if not post_data.get("ok"):
            err = post_data.get("error") or "chat.postMessage failed"
            raise ValueError(f"Slack API error: {err}")

    return SlackResult(posted=True, detail="Slack OK: DM delivered")
