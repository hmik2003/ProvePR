# TicketTrace

AI-assisted **PR ↔ Jira/PRD** reviewer.

Connect any GitHub repo to any Jira board: TicketTrace reads the ticket requirements, reviews the PR diff with **Hermes Agent + Gemini**, comments on the PR, and can notify Slack.

**Stack (locked):** Nous Research **Hermes Agent** + **Google Gemini** API key.  
**Trigger (later):** GitHub Action on PRs to `staging` (configurable).  
**Dev account:** personal GitHub `hmik2003` first; company pilots later.

Living product context: [`PROJECT.md`](./PROJECT.md)

---

## Sprint model

Every sprint ships a **working increment**.

| Sprint | Working product |
|--------|-----------------|
| **1 (current)** | Local Python package + `smoke` CLI |
| 2 | GitHub + Jira read connections |
| 3 | Fetch PR diff + Jira PRD |
| 4 | Hermes + Gemini review (terminal) |
| 5 | Post PR comment + Slack |
| 6 | HTTP trigger endpoint |
| 7 | GitHub Action on personal repo |
| 8 | Cloud Run deploy |
| 9 | First company pilot handoff |

---

## Sprint 1 — run it

### Prerequisites

- Python 3.11+ (3.12/3.13 preferred; 3.14 may work)
- Windows PowerShell is fine

### Setup

```powershell
cd C:\Users\HP\Desktop\TicketTrace
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
```

### Smoke (working product)

```powershell
python -m tickettrace smoke
```

Expected: `Sprint 1 OK` and a checklist of keys for later sprints (missing is normal until you fill `.env`).

### Tests

```powershell
pytest -q
```

---

## Secrets

1. Copy `.env.example` → `.env`
2. Fill values only when a sprint asks for them
3. Never commit `.env`

You will get **step-by-step instructions** in chat when GitHub / Jira / Gemini / Slack keys are required.

---

## Do not paste secrets into chat

When a key is ready, put it in `.env` yourself. Tell the agent “keys are in `.env`” — do not paste token values into the conversation.
