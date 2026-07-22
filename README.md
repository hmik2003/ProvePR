# Spatial AI Reviewer

AI-assisted **PR ↔ Jira PRD** reviewer for SpatialSense.

**Stack (locked):** Nous Research **Hermes Agent** + **Google Gemini** API key.  
**Trigger (later):** GitHub Action on PRs to `staging`.  
**Dev account:** personal GitHub `hmik2003` first, org later.

Living product context: [`PROJECT.md`](./PROJECT.md)

---

## Sprint model

Every sprint ships a **working increment**. We do not wait for Cloud Run to have something useful.

| Sprint | Working product |
|--------|-----------------|
| **1 (current)** | Local Python package + `smoke` CLI |
| 2 | GitHub + Jira read connections |
| 3 | Hermes + Gemini review of a real PR/ticket (terminal) |
| 4 | Post PR comment + Slack |
| 5 | HTTP trigger endpoint |
| 6 | GitHub Action on personal repo |
| 7 | Cloud Run (needs supervisor GCP) |
| 8 | SpatialSense handoff |

---

## Sprint 1 — run it

### Prerequisites

- Python 3.11+ (3.12/3.13 preferred; 3.14 may work)
- Windows PowerShell is fine

### Setup

```powershell
cd C:\Users\HP\Desktop\Staging-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
```

### Smoke (working product)

```powershell
python -m spatial_ai_reviewer smoke
```

Expected: `Sprint 1 OK` and a checklist of keys for later sprints (missing is normal).

### Tests

```powershell
$env:PYTHONPATH = "src"
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
