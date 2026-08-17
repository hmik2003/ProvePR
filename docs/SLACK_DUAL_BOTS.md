# Dual Slack bots — Dev vs PM DMs

ProvePR can DM you from **two Slack apps** so review noise and ticket-gate noise stay in separate threads.

## Routing

| Kind | Used by | Env token |
|------|---------|-----------|
| **dev** | PR review, skip-notify | `SLACK_DEV_BOT_TOKEN` → else `SLACK_BOT_TOKEN` |
| **pm** | `prd-gate` (Story/Bug/Task) | `SLACK_PM_BOT_TOKEN` → else `SLACK_BOT_TOKEN` |

Shared: `SLACK_DM_USER_ID` (your Slack user id).

If only `SLACK_BOT_TOKEN` is set, both kinds use it (old behavior).

## Create the second app (PM)

You already have one bot (treat it as **Dev** or leave as legacy fallback).

1. Open https://api.slack.com/apps → **Create New App** → From scratch  
2. Name: e.g. **KodiQA PM** · pick your workspace  
3. **OAuth & Permissions** → Bot Token Scopes:
   - `chat:write`
   - `im:write`
4. **Install to Workspace** → copy **Bot User OAuth Token** (`xoxb-…`)  
5. In `.env`:

```env
SLACK_DM_USER_ID=U0BAP3SJMEV
SLACK_DEV_BOT_TOKEN=xoxb-...   # existing / Dev app
SLACK_PM_BOT_TOKEN=xoxb-...    # new PM app
# Optional: keep or clear SLACK_BOT_TOKEN (fallback only)
```

6. Push to Cloud Run:

```powershell
python scripts/set_cloudrun_env.py
```

7. Smoke:
   - Move a Story → To Do → DM from **KodiQA PM**
   - Open a ticketed PR → DM from **KodiQA Dev** (or your Dev app name)

## Rename tip

In Slack app settings → **Basic Information** → display name / bot name:
- Dev app → `KodiQA Dev`
- PM app → `KodiQA PM`
