# Sprint 5 — Post PR Comment + Slack (or stub) Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox syntax.

**Goal:** After a cost-guarded Gemini review, post the result as a GitHub PR comment; notify Slack via webhook if configured, otherwise print a clear stub (no blocker).

**Architecture:** Extend `GitHubClient` with `create_issue_comment`. Add `slack_notify` helper. Extend `provepr review --yes --post` to publish. Slack remains optional for Sprint 5 completion.

**Tech Stack:** Existing `httpx` clients; Slack Incoming Webhooks JSON POST.

## Global Constraints

- Still require `--yes` for Gemini spend (one call)
- `--post` requires `--yes`
- Never print tokens/webhooks
- Supervisor: **not required** if GitHub PAT can comment on personal repo; Slack admin only if you want a real webhook now

## Done when

- Live comment appears on PR #1
- Without `SLACK_WEBHOOK_URL`, CLI prints `Slack stub: skipped`
- With webhook set, Slack receives a short message
- Tests pass with mocks
