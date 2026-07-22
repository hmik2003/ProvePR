# SpatialSense AI PR Reviewer — Project Context

> Living document. Update at the end of every phase. No stale or missing decisions.

**Last updated:** 2026-07-22  
**Status:** Sprint 1 (Phase 0) complete — ready for Sprint 2 keys  
**Partners:** Lead QA (hmik2003) + Lead SE (Cursor agent)

---

## 1. Goal

Build an AI pipeline that, when a PR is opened/updated toward **staging**:

1. Finds the matching **Jira** ticket (from PR title → branch → body)
2. Reads the ticket PRD / requirements (**read-only**)
3. Reads the GitHub PR **diff**
4. Uses **Nous Research Hermes Agent** + a **Gemini** model to **review** code vs requirements (static AI review — not a full test runner)
5. Posts a review **comment on the GitHub PR**
6. Notifies the team on **Slack**

Prove everything first on personal GitHub (`hmik2003`), then port to SpatialSense + org GCP.

### Agent count (plain English)

- **One Hermes Agent** does the job end-to-end (one “virtual SQA reviewer” per PR run).
- Inside that one agent there is **one Gemini model** doing the thinking.
- Hermes may call several **tools** (Jira fetch, GitHub diff, post comment, Slack) — those are helpers, **not** separate agents.
- We are **not** starting with a multi-agent swarm (no separate “security agent”, “UI agent”, etc.). That can be a later upgrade if quality needs it.

### What step 4 is (and is not)

| It IS | It is NOT |
|-------|-----------|
| AI **requirements vs code** review (like a senior SQA reading a PR) | Clicking through the app / E2E UI automation |
| Static analysis of the **diff** against the PRD | Replacing Selenium/Playwright/Cypress suites |
| Finding gaps, risks, missing acceptance criteria | Guaranteeing the feature works in staging |
| A **first-pass gate** before human review | A replacement for human SQA sign-off |

---

## 1b. SQA review strategy (how Hermes “tests” against the PRD)

Think of Hermes as an automated **PR review checklist**, not a robot that opens the browser.

**Input A — Requirements (Jira):** summary, description, acceptance criteria / PRD text.  
**Input B — Change under test (GitHub):** only the PR **diff** (added/removed/changed lines), plus PR title/description.  
**Process:** Gemini (via Hermes) compares A vs B using fixed review dimensions.  
**Output:** Structured findings posted as a PR comment (pass/fail-ish coverage + risks + questions).

### Review dimensions (v1 checklist)

1. **Requirements coverage** — Does the diff appear to implement each stated requirement / AC?
2. **Missing / partial features** — Anything in the PRD with no matching code change?
3. **Acceptance criteria mapping** — AC-by-AC: Covered / Partial / Not found / Unclear
4. **Functional risk** — Logic bugs, wrong conditions, missing null/empty handling visible in the diff
5. **Edge cases** — Empty input, auth failure, permissions, retries, bad data (called out if relevant to the ticket)
6. **Regression smell** — Changes that may break adjacent behavior (renames, shared helpers, API contract shifts)
7. **Security / data basics** — Secrets in code, obvious authz gaps, unsafe input handling (lightweight, not a full pen-test)
8. **Testability gap** — PRD says X but PR has no tests / weak tests when tests are expected
9. **Clarity / questions** — Ambiguous PRD items the agent cannot verify from the diff alone

### Output format we will aim for on each PR

- **Verdict:** Requirements largely met / Partial / Insufficient evidence
- **AC coverage table:** each criterion → Covered / Partial / Missing / Unclear
- **Findings:** severity (Blocker / Major / Minor / Info) + file/area if known
- **Suggested human SQA focus:** what a real tester should still verify manually or in staging
- **Open questions:** for author / product if PRD or code is ambiguous

### Honest limits (QA ownership note)

- Can only “see” what is in the **ticket text** + **PR diff** (and later, optionally linked docs).
- Cannot prove runtime behavior without later adding real test execution (unit/integration/E2E) as a separate phase.
- Quality depends on ticket quality: vague PRDs → weaker reviews. Enforcing good AC in Jira is part of making this agent useful.

---

## 2. Locked decisions

| Decision | Choice | Notes |
|----------|--------|-------|
| Trigger | GitHub Action on PR → `staging` | Not Jira status transitions (humans forget) |
| Agent runtime | **Nous Research Hermes Agent** | Supervisor: “Hermes is the way forward” |
| LLM provider | **Google Gemini** (AI Studio API key) | Supervisor: “Gemini ki key laga” |
| Model selection | Choose deliberately (Pro for deep review, Flash for cheaper/faster) | Supervisor: “model soch samajh kar lagana” |
| Preferred Gemini endpoint | Native `https://generativelanguage.googleapis.com/v1beta` | Not the `/openai` compatibility URL |
| Env var for key | `GOOGLE_API_KEY` or `GEMINI_API_KEY` | Hermes accepts either |
| Initial candidate models | Pro-class for PR reviews; Flash for later cost tuning | Exact ID picked after `hermes model` / AI Studio availability |
| Framework | Hermes first; **no LangChain** unless we hit a hard limit | Avoid Gemini-chat over-engineering |
| Hosting (later) | Google **Cloud Run** | Supervisor path; needs org GCP access |
| GitHub (dev) | Personal account **hmik2003** | Org SpatialSense later |
| Jira | Org Jira, **read-only** | Never write/update tickets in early phases |
| Secrets | Local `.env` only; never commit; never bake into Docker image | Cloud Run = env vars / Secret Manager |

---

## 3. Architecture (target)

```text
[PR opened/updated → staging]
            │
            ▼
   [GitHub Action]
   extract Jira ID (title → branch → body)
            │
            ▼
   [HTTP trigger → service on Cloud Run]
            │
            ▼
   [Hermes Agent + Gemini model]
      ├─ tool: fetch Jira ticket (R/O)
      ├─ tool: fetch GitHub PR diff
      ├─ reason: requirements vs code
      ├─ tool: post GitHub PR comment
      └─ tool: Slack notify
```

**Local-first path:** same Hermes review logic runs on laptop before Cloud Run exists.

---

## 4. Ideal naming convention (ticket ↔ PR)

| Item | Example |
|------|---------|
| Jira key | `SENSE-105` (use real project key when known) |
| Jira summary | Add password reset button to the login screen |
| PR title | `SENSE-105: Add password reset button to the login screen` |
| Branch | `feature/SENSE-105-password-reset` |

If no Jira ID is found, the Action skips the review (safe failure).

---

## 5. Roadmap

| Phase | What | Supervisor needed? | Status |
|-------|------|--------------------|--------|
| **0 / Sprint 1** | Scaffold repo, smoke CLI, tests, docs | No | **Done** |
| **1 / Sprint 2** | GitHub + Jira read connections | No (unless Jira token lacks read) | Next |
| **2 / Sprint 3** | Fetch real PR diff + Jira PRD text | No | Pending |
| **3 / Sprint 4** | Hermes + Gemini local AI review | No (need Gemini key; billing recommended) | Pending |
| **4 / Sprint 5** | Post GitHub PR comment + Slack (or stub) | Maybe Slack admin | Pending |
| **5 / Sprint 6** | HTTP wrapper for triggers | No | Pending |
| **6 / Sprint 7** | GitHub Action on personal `hmik2003` repo → `staging` | No | Pending |
| **7 / Sprint 8** | Deploy to Google Cloud Run | **Yes — GCP project/IAM** | Pending |
| **8 / Sprint 9** | Port to SpatialSense + org Slack | **Yes — repo admin + team buy-in** | Pending |

---

## 6. Credentials checklist (who provides what)

| Secret | Who | When |
|--------|-----|------|
| GitHub PAT (personal) | You | Phase 1 |
| Jira email + API token (read) | You | Phase 1 |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | You (AI Studio) | Phase 3 |
| Slack webhook / bot | You or Slack admin | Phase 4 |
| GCP project + deploy rights | Supervisor | Phase 7 |
| SpatialSense repo secrets + workflow rights | Supervisor / repo admin | Phase 8 |

---

## 7. Out of scope (for now)

- Writing/updating Jira tickets
- Replacing human code review
- LangChain-first architecture
- Unauthenticated public Cloud Run endpoints
- Committing secrets or `.env` files
- **Custom monitoring dashboard (v1)** — deferred; see §7b

### 7b. Dashboard decision (2026-07-22)

| Question | Answer |
|----------|--------|
| Good idea for v1? | **No** — builds a second product before the pipeline is proven |
| Feasible later? | **Yes** — after reviews are reliable and we store run results |
| Maintainable as a custom app now? | **Poor** — UI + auth + DB + hosting + sync with GitHub = ongoing cost for an SQA-led first ship |

**v1 monitoring (no custom UI):** GitHub PR comments + Actions history + Slack alerts.  
**Optional Phase 9+:** lightweight history API / simple dashboard **only if** we already persist each run (PR, Jira ID, verdict, comment URL, timestamp). Until then, GitHub/Slack *are* the dashboard.

---

## 8. Working agreement

- Implement **one phase at a time**; commit after each phase
- Keep this file accurate after every phase (status + decisions)
- Lead QA owns quality criteria and acceptance; Lead SE owns implementation
- Test on personal GitHub before touching SpatialSense

---

## 9. Open items

- [ ] Exact Gemini model ID after first `hermes model` / AI Studio check
- [ ] Real Jira project key (e.g. `SENSE` or other)
- [ ] Personal test repo name under `hmik2003` (create in Phase 0/1)
- [ ] Where PRD text lives in Jira (description vs custom field / AC)
- [ ] Company Slack vs personal Slack for early tests
- [ ] Revisit custom dashboard after Phase 8 (only if GitHub+Slack monitoring is not enough)

---

## 10. Phase log

| Date | Phase | Notes |
|------|-------|-------|
| 2026-07-22 | Design | Locked Hermes Agent + Gemini; GitHub trigger; personal-first rollout |
| 2026-07-22 | Design | Dashboard deferred to post-v1; use GitHub + Slack as monitor |
| 2026-07-22 | Sprint 1 | Scaffold + `python -m spatial_ai_reviewer smoke`; tests pass |
