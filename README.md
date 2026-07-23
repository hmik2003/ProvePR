# ProvePR — AI PR Reviewer

Prove the PR matches the ticket.

Connect any GitHub repo to any Jira board: **ProvePR** reads the requirements, reviews the PR diff with **Hermes Agent + Gemini**, comments on the PR, and can notify Slack.

**Stack (locked):** Nous Research **Hermes Agent** + **Google Gemini** API key.  
**Deploy unit:** **one Docker image** (ProvePR + Hermes + deps) → Cloud Run.  
**Dev account:** personal GitHub `hmik2003` first; company pilots later.

Living product context: [`PROJECT.md`](./PROJECT.md)  
Security / least privilege: [`SECURITY.md`](./SECURITY.md)

---

## Sprint model

| Sprint | Working product |
|--------|-----------------|
| 1–7 | CLI + Action + HTTP serve (done) |
| **Hermes + Docker** | Tool-using Hermes review + single image (done) |
| **8 (in progress)** | Cloud Run deploy scripts ready — needs your GCP project |
| 9 | First company pilot handoff |

---

## Setup (local)

Hermes requires **Python 3.11–3.13** (not 3.14). Recommended:

```powershell
cd C:\Users\HP\Desktop\ProvePR
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = "src"
$env:HERMES_ENABLE_PROJECT_PLUGINS = "1"
```

Copy `.env.example` → `.env` and fill keys as needed.

---

## Review (Hermes + Gemini)

```powershell
# Free dry-run
python -m provepr review

# Hermes tool loop (up to 8 Gemini turns) — uses get_jira_prd / get_pull_request / get_pull_request_diff
python -m provepr review --yes

# Review + GitHub comment + Slack DM
python -m provepr review --yes --post
```

**Cost:** `--yes` is required. Hermes may call Gemini **multiple times** (capped at **8** turns). If `hermes-agent` is missing, ProvePR falls back to a single-shot Gemini call.

ProvePR tools only (no terminal/browser): Jira PRD (parent + subtasks) + GitHub PR meta + unified diff.

**Policies baked in:**
- **1 ticket ↔ 1 PR** — exactly one Jira key in the PR title (multiple keys skip the Action).
- **Development panel** — comment advises if the PR is not linked on the Jira ticket; **non-blocking**.
- **PRD quality gate (soft)** — `python -m provepr prd-gate --ticket PROV-10` checks Story mandatory sections (Goals, Persona, User stories, Functional reqs, AC, Success metrics, Scope). Does **not** block To Do yet.
- **Skip notify** — if a PR has no Jira key (or multiple keys in the title), review is skipped (no Gemini) but QA gets a Slack DM + short PR comment via `skip-notify`.

---

## Single Docker image (supervisor path)

```powershell
docker build -t provepr .
docker run --rm -p 8080:8080 --env-file .env -e PORT=8080 provepr
```

- `GET http://localhost:8080/health`
- `POST /v1/review` with `Authorization: Bearer <PROVEPR_TRIGGER_SECRET>`

Secrets stay in env / Secret Manager — **never** baked into the image. Cloud Run = run this same image.

---

## HTTP serve (without Docker)

```powershell
python -m provepr serve
```

Honors `PORT` (Cloud Run) or `PROVEPR_HTTP_PORT` (local).

---

## Sprint 8 — Cloud Run (single image)

Deploy unit is the repo root [`Dockerfile`](./Dockerfile) (ProvePR + Hermes + deps).

**You need:** a GCP project (billing on) + [`gcloud` CLI](https://cloud.google.com/sdk/docs/install). Local Docker is optional — the script uses **Cloud Build**.

```powershell
# From repo root (after gcloud auth login)
.\scripts\deploy-cloud-run.ps1 -ProjectId "YOUR_GCP_PROJECT" -Region "us-central1"
```

Then set secrets on the service (never bake into the image):

```powershell
gcloud run services update provepr --region us-central1 --update-env-vars `
  "PROVEPR_TRIGGER_SECRET=...,GITHUB_TOKEN=...,JIRA_SERVER_URL=...,JIRA_EMAIL=...,JIRA_API_TOKEN=...,GOOGLE_API_KEY=..."
```

Verify: `GET $SERVICE_URL/health` and authenticated `POST /v1/review`.

Full checklist: [`docs/superpowers/plans/2026-07-23-sprint-8-cloud-run.md`](./docs/superpowers/plans/2026-07-23-sprint-8-cloud-run.md)

---

## GitHub Action (interim)

Workflow still checks out ProvePR into the runner until Cloud Run URL is wired. After Sprint 8, Actions can become a thin `POST` to the service.

---

## Tests

```powershell
pytest -q
```

---

## Secrets

1. Copy `.env.example` → `.env`
2. Never commit `.env`
3. Do not paste token values into chat
4. Follow least privilege in [`SECURITY.md`](./SECURITY.md) (Jira browse-only bot; GitHub comment-only write)
