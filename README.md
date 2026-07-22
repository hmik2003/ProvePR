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
| **2 (current)** | GitHub + Jira read connections (`connect` CLI) |
| 3 | Fetch PR diff + Jira PRD |
| 4 | Hermes + Gemini review (terminal) |
| 5 | Post PR comment + Slack |
| 6 | HTTP trigger endpoint |
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
