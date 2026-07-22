# ProvePR — AI PR Reviewer

Prove the PR matches the ticket.

Connect any GitHub repo to any Jira board: **ProvePR** reads the requirements, reviews the PR diff with **Hermes Agent + Gemini**, comments on the PR, and can notify Slack.

**Stack (locked):** Nous Research **Hermes Agent** + **Google Gemini** API key.  
**Trigger (later):** GitHub Action on PRs to `staging` (configurable).  
**Dev account:** personal GitHub `hmik2003` first; company pilots later.

Living product context: [`PROJECT.md`](./PROJECT.md)

---

## Sprint model

Every sprint ships a **working increment**.

| Sprint | Working product |
|--------|-----------------|
| 1 | Local Python package + `smoke` CLI |
| 2 | GitHub + Jira read connections (`connect` CLI) |
| 3 | Fetch PR diff + Jira PRD (`fetch` CLI) |
| 4 | Single-shot Gemini `review` (cost-guarded; Hermes loop later) |
| 5 | Post PR comment + Slack (or stub) |
| **6 (next)** | HTTP trigger endpoint |
| 7 | GitHub Action on personal repo |
| 8 | Cloud Run deploy |
| 9 | First company pilot handoff |

---

## Setup

```powershell
cd C:\Users\HP\Desktop\ProvePR
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
```

---

## Sprint 1 — smoke

```powershell
python -m provepr smoke
```

Expected: `Sprint 1 OK` (no API keys required).

---

## Sprint 2 — connect (GitHub + Jira)

1. Copy `.env.example` → `.env`
2. Fill Sprint 2 keys: `GITHUB_TOKEN`, `JIRA_SERVER_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
3. Run:

```powershell
python -m provepr connect
```

Expected: `GitHub OK`, `Jira OK`, `=== Sprint 2 OK ===`

Optional deeper peeks in `.env`:

```env
GITHUB_TEST_REPO=hmik2003/your-repo
JIRA_TEST_TICKET=PROJ-123
```

Check one side only:

```powershell
python -m provepr connect --github
python -m provepr connect --jira
```

---

## Sprint 3 — fetch (PR diff + Jira PRD)

Set targets in `.env` (or pass flags):

```env
GITHUB_TEST_REPO=hmik2003/ProvePR
GITHUB_TEST_PR_NUMBER=1
JIRA_TEST_TICKET=PROJ-123
```

```powershell
python -m provepr fetch
# or:
python -m provepr fetch --repo hmik2003/ProvePR --pr 1 --ticket PROJ-123
```

Expected: PR title + diff preview, Jira summary + PRD preview, `=== Sprint 3 OK ===`.

**How to choose `JIRA_TEST_TICKET`:** open any issue you can view in Jira → copy the key (`ABC-42`) → paste into `.env`. It does **not** need to match the GitHub PR for this sprint. Full checklist: [`PROJECT.md` §9b](./PROJECT.md).

---

## Sprint 4 — review (Gemini, cost-guarded)

Requires `GOOGLE_API_KEY` or `GEMINI_API_KEY` in `.env`. Default model: `gemini-flash-lite-latest` (override with `GEMINI_MODEL`).

**Budget rule:** Hermes multi-turn loops are deferred. ProvePR calls Gemini **once** per review, and only if you pass `--yes`.

```powershell
# Free dry-run (no Gemini spend)
python -m provepr review

# Spend one Gemini call
python -m provepr review --yes

# Review + post GitHub PR comment (+ Slack if webhook set, else stub)
python -m provepr review --yes --post
```

Optional Slack: set `SLACK_WEBHOOK_URL` in `.env` (Incoming Webhook). **No supervisor needed** to finish Sprint 5 — stub is enough. Involve Slack admin only if you want a real channel ping.

### Tests

```powershell
pytest -q
```

---

## Secrets

1. Copy `.env.example` → `.env`
2. Fill values only when a sprint asks for them
3. Never commit `.env`

Do not paste token values into chat — put them in `.env` and say “keys are in `.env`”.
