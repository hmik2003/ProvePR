# ProvePR — Production rollout (private pilots → company products)

> Living guide. Update when a phase completes.

## Recommendation: PM vs Dev — ship **both**, wire **gradually**

You do **not** need two Cloud Run deploys. Dev (`/v1/review`, `/v1/pr-hook`) and PM (`/v1/prd-gate`) already share one image.

| Approach | Verdict |
|----------|---------|
| Deploy PM only first | Weak — company value is the PR review; PM gate alone doesn’t prove the product |
| Deploy Dev only, PM “later” as a second project | Waste — same service, same secrets, delays Jira Automation practice |
| **Keep one Cloud Run; pilot Dev + PM together on private sandbox; add company boards/repos one-by-one** | **Best** |

### Suggested sequence

1. **Private sandbox (now)** — `provepr-demo-shop` + Jira `PROV`  
   - Thin GitHub Action → Cloud Run (`/v1/pr-hook`)  
   - Jira Automation on **PROV only** → `/v1/prd-gate`  
2. **More private repos** — copy the thin workflow; install KodiQA App; add 2 secrets  
3. **Company pilot board/repo** — bot Jira user + App install + same Action template  
4. **Scale** — more products after one successful company pilot

**Why not “PM first”?** Creators feel the gate before eng trusts the review. Run both on PROV so you learn Automation + Action failure modes together, without risking company boards.

**Why not wait forever on PM?** Automation against a live URL is the only way to validate delay / In Progress safety net. Do it on PROV while you’re still the only user.

---

## Architecture (production-like)

```text
[Private or company repo]
   PR → staging
        │
        ▼
   Thin GitHub Action  (no ProvePR checkout)
        │  POST /v1/pr-hook
        ▼
   Cloud Run (single image)
        ├─ review + GitHub comment + Slack   (Dev)
        └─ /v1/prd-gate ← Jira Automation    (PM)
```

**Cloud Run URL (current):** `https://provepr-2f6eho3aiq-uc.a.run.app`

---

## Add a new private repo (Dev) — checklist

1. Install **KodiQA** GitHub App on the repo (Pull requests: Read & write).
2. Copy [`.github/workflows/provepr-cloudrun.yml`](./github-action-cloudrun.yml) into the repo (target branch = your integration branch, usually `staging`).
3. Repo Actions secrets:
   - `PROVEPR_URL` = `https://provepr-2f6eho3aiq-uc.a.run.app`
   - `PROVEPR_TRIGGER_SECRET` = same as Cloud Run
4. Open a PR titled `PROJ-123: …` → staging; confirm KodiQA comment + Slack.

No per-repo Jira/Gemini/Slack secrets — those live on Cloud Run only.

---

## Wire Jira Automation (PM) — PROV first

**Rule A — Story → To Do**

- When: Issue transitioned → To Do; Type = Story; Project = PROV  
- Then: Send web request  
  - URL: `https://provepr-2f6eho3aiq-uc.a.run.app/v1/prd-gate`  
  - Method: POST  
  - Headers: `Authorization: Bearer <PROVEPR_TRIGGER_SECRET>`, `Content-Type: application/json`  
  - Body: `{"issue":{"key":"{{issue.key}}"},"trigger":"to_do"}`

**Rule B — Bug/Task → To Do (delayed)**

- When: Issue transitioned → To Do; Type in (Bug, Task); Project = PROV  
- Then: Delay **15–30 minutes**  
- Then: same web request with `"trigger":"to_do"`

**Rule C — Bug/Task → In Progress (safety net)**

- When: Issue transitioned → In Progress; Type in (Bug, Task); Project = PROV  
- Then: same web request with `"trigger":"in_progress"`  
  (Cloud Run no-ops if a prior KodiQA comment already said Ready)

Do **not** enable these on company boards until PROV has run clean for a while.

---

## Secrets map

| Secret | Where |
|--------|--------|
| `PROVEPR_TRIGGER_SECRET` | Cloud Run + each repo Action |
| Jira / Gemini / Slack / GitHub App | **Cloud Run only** |
| `KODIQA_APP_*` | Only if a repo still uses the fat checkout Action (legacy) |

Refresh with `python scripts/set_cloudrun_env.py` after rotating `.env`.

---

## Done means (private pilot exit criteria)

- [ ] `/health` OK on Cloud Run  
- [ ] Story + Bug + Task gates on PROV tickets (Ready / Needs work)  
- [ ] Ticketed PR → staging gets KodiQA review via **thin** Action  
- [ ] No-ticket PR gets skip-notify via same Action  
- [ ] Jira Automation rules A/B/C live on PROV only  
- [ ] Actions `JIRA_API_TOKEN` not required on repos using Cloud Run hook  
