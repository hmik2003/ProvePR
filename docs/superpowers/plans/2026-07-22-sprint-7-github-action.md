# Sprint 7 — GitHub Action on PR → staging

**Goal:** When a PR targets `staging`, extract a Jira key and run `provepr review --yes --post` in CI.

**Architecture:** Workflow runs on `ubuntu-latest` with repo secrets (Jira/Gemini/Slack). Uses runner-local ProvePR (no Cloud Run yet — Sprint 8). Skips safely if no Jira key.

**Secrets needed on repo:** `JIRA_SERVER_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `GOOGLE_API_KEY`, optional `SLACK_BOT_TOKEN` + `SLACK_DM_USER_ID`, optional `PROVEPR_GITHUB_TOKEN` (PAT) if default `GITHUB_TOKEN` lacks comment rights.
