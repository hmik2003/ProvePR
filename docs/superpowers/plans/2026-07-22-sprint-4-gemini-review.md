# Sprint 4 — Cost-Safe Gemini Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `python -m provepr review` that compares a Jira PRD to a GitHub PR diff with **one** Gemini `generateContent` call and prints a structured SQA-style review.

**Architecture:** Reuse Sprint 3 fetch helpers. Call Google’s **native** Gemini API (`generativelanguage.googleapis.com/v1beta`) directly from ProvePR — **single request, no agent loop**. Full Hermes multi-turn tool loops are deferred because they make several model calls per turn and risk burning the supervisor’s **$5** budget unnoticed.

**Tech Stack:** Python 3.11+, `httpx`, existing clients, `pytest` + `respx`

## Global Constraints

- Never print API keys
- Default model: cheap Flash (`gemini-2.0-flash`, overridable via `GEMINI_MODEL`)
- **Exactly one** Gemini HTTP call per `review` invocation; no automatic retries
- Require `--yes` for live calls; default is dry-run (shows sizes only)
- Truncate oversized PRD/diff before send
- Product: **ProvePR** / package `provepr`
- Supervisor: already provided key + $5 cap — respect it

## Cost-guard decision (lock in PROJECT.md)

| Approach | Sprint 4 choice |
|----------|-----------------|
| Hermes agent chat loop | **Deferred** (multi-call burn risk on $5) |
| Single-shot native Gemini | **Ship now** as `provepr review` |
| Hermes later | When budget allows / after Sprint 5 posting |

## File Structure

| File | Responsibility |
|------|----------------|
| `src/provepr/config.py` | `GeminiSettings`, `require_gemini_settings`, defaults |
| `src/provepr/gemini_client.py` | One-shot `generate_text(...)` |
| `src/provepr/review.py` | Build prompt from PRD+diff; dry-run / live review |
| `src/provepr/__main__.py` | `review` subcommand + `--yes` |
| `tests/test_gemini_client.py` | Mocked HTTP |
| `tests/test_review.py` | Dry-run + mocked live |
| `README.md` / `PROJECT.md` / `.env.example` | Docs + cost notes |

---

### Task 1: Gemini settings + one-shot client

**Interfaces:**
- `GeminiSettings(api_key: str, model: str)`
- `require_gemini_settings() -> GeminiSettings` (GOOGLE_API_KEY preferred, else GEMINI_API_KEY)
- Default model: `gemini-2.0-flash`
- `GeminiClient.generate_text(system: str, user: str) -> str` — **one** POST, `raise_for_status`, no retry

- [ ] Tests (respx) + implement + pytest PASS

---

### Task 2: `review` CLI with cost guards

**Interfaces:**
- `run_review(*, repo, pr, ticket, yes: bool = False) -> int`
- If `yes` is False: print target, char counts, model, “pass --yes to spend”; exit 0 **without** calling Gemini
- If `yes` is True: fetch PRD+diff, truncate, **one** Gemini call, print review markdown
- Truncation: PRD max 12_000 chars, diff max 40_000 chars

- [ ] Tests + implement + wire CLI
- [ ] Live: dry-run first, then **one** `--yes` against PR #1 + SX-2869
- [ ] Docs + commit

**Done when:** dry-run is free; one paid review works; docs warn about $5 budget.
