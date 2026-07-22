"""Slack notify — prefer personal DM via bot; webhook optional; stub if unset."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from provepr.config import load_env

SLACK_API = "https://slack.com/api"


@dataclass(frozen=True)
class SlackResult:
    posted: bool
    detail: str


def notify_slack(text: str) -> SlackResult:
    """
    Notify order:
    1) SLACK_BOT_TOKEN + SLACK_DM_USER_ID → open DM and post (personal only)
    2) SLACK_WEBHOOK_URL → Incoming Webhook (channel; legacy)
    3) else stub
    """
    load_env()
    bot_token = (os.getenv("SLACK_BOT_TOKEN") or "").strip()
    dm_user = (os.getenv("SLACK_DM_USER_ID") or "").strip()
    webhook = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()

    if bot_token and dm_user:
        return _dm_via_bot(bot_token=bot_token, user_id=dm_user, text=text)

    if bot_token and not dm_user:
        return SlackResult(
            posted=False,
            detail="Slack stub: SLACK_BOT_TOKEN set but SLACK_DM_USER_ID missing",
        )

    if webhook:
        response = httpx.post(webhook, json={"text": text}, timeout=30.0)
        response.raise_for_status()
        return SlackResult(posted=True, detail="Slack OK: webhook delivered")

    return SlackResult(
        posted=False,
        detail=(
            "Slack stub: skipped "
            "(set SLACK_BOT_TOKEN + SLACK_DM_USER_ID for personal DM)"
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
