# Sprint 8 — Cloud Run (single Docker image)

**Goal:** Deploy ProvePR as one container on Google Cloud Run so reviews run via `POST /v1/review` instead of checking out the tool into every repo.

**Architecture:** Same image as local `Dockerfile` → Artifact Registry (or Cloud Build) → Cloud Run service. Secrets via Cloud Run env / Secret Manager. GitHub Action becomes a thin HTTP client (follow-up once URL exists).

## Prerequisites (human)

- [ ] GCP project with billing
- [ ] `gcloud` CLI authenticated (`gcloud auth login` + `gcloud config set project PROJECT_ID`)
- [ ] APIs enabled: `run`, `artifactregistry`, `cloudbuild` (script enables these)
- [ ] Docker Desktop (for local image prove) **or** Cloud Build only

## Secrets to set on the Cloud Run service

| Env var | Required |
|---------|----------|
| `PROVEPR_TRIGGER_SECRET` | Yes (Bearer for `/v1/review`) |
| `GITHUB_TOKEN` | Yes (PAT or GitHub App token with PR comment rights) |
| `JIRA_SERVER_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` | Yes |
| `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Yes |
| `SLACK_BOT_TOKEN` / `SLACK_DM_USER_ID` | Optional |
| `GEMINI_MODEL` | Optional |
| `HERMES_ENABLE_PROJECT_PLUGINS` | `1` (image default) |

## Deploy

PowerShell (from repo root):

```powershell
.\scripts\deploy-cloud-run.ps1 -ProjectId "YOUR_GCP_PROJECT" -Region "us-central1"
```

Or bash:

```bash
./scripts/deploy-cloud-run.sh YOUR_GCP_PROJECT us-central1
```

## Verify

```bash
curl -sS "$SERVICE_URL/health"
curl -sS -X POST "$SERVICE_URL/v1/review" \
  -H "Authorization: Bearer $PROVEPR_TRIGGER_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"repo":"hmik2003/provepr-demo-shop","pr":6,"ticket":"PROV-6","post":false}'
```

## Done when

- [ ] `/health` returns ok on Cloud Run URL
- [ ] Authenticated `/v1/review` completes a dry-ish review (`post:false`)
- [ ] Docs list the service URL for Action wiring (Sprint 8b)
