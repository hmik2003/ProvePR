# Sprint 3 — Fetch PR Diff + Jira PRD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch a real GitHub PR diff and a real Jira ticket’s requirement text locally, and print a clear preview via `python -m provepr fetch`.

**Architecture:** Extend existing `GitHubClient` / `JiraClient` with read helpers. Add a thin `fetch` module that loads targets from CLI flags or `.env`, pulls PR metadata + unified diff, pulls issue summary/description (ADF → plain text), and prints truncated previews (never secrets). No Hermes/Gemini yet — that is Sprint 4.

**Tech Stack:** Python 3.11+, `httpx`, `pytest`, `respx` (existing)

## Global Constraints

- Never commit `.env` or print tokens
- Read-only GitHub + Jira only
- Personal repo `hmik2003/ProvePR` is the default test target
- Product name **ProvePR** / package `provepr`
- Supervisor: **not required** for Sprint 3

## File Structure

| File | Responsibility |
|------|----------------|
| `src/provepr/github_client.py` | Add `get_pull_request`, `get_pull_request_diff` |
| `src/provepr/jira_client.py` | Keep `get_issue`; optionally request specific fields |
| `src/provepr/jira_text.py` | Convert Jira ADF / string description → plain text |
| `src/provepr/fetch.py` | Orchestrate fetch + print previews |
| `src/provepr/__main__.py` | Add `fetch` subcommand |
| `tests/test_github_client.py` | PR + diff mocked tests |
| `tests/test_jira_text.py` | ADF → text tests |
| `tests/test_fetch.py` | Orchestration with fakes |
| `README.md` / `PROJECT.md` / `.env.example` | Sprint 3 docs |

---

### Task 1: GitHub PR + diff helpers

**Files:**
- Modify: `src/provepr/github_client.py`
- Modify: `tests/test_github_client.py`

**Interfaces:**
- Consumes: existing `GitHubClient`
- Produces:
  - `get_pull_request(self, full_name: str, number: int) -> dict`
  - `get_pull_request_diff(self, full_name: str, number: int) -> str`  
    (`Accept: application/vnd.github.diff`)

- [ ] **Step 1: Write failing tests** for PR JSON + diff text (respx)
- [ ] **Step 2: Implement methods**
- [ ] **Step 3: pytest tests/test_github_client.py — PASS**

---

### Task 2: Jira description → plain text

**Files:**
- Create: `src/provepr/jira_text.py`
- Create: `tests/test_jira_text.py`

**Interfaces:**
- Produces:
  - `def adf_to_text(node: object) -> str`
  - `def issue_prd_text(issue: dict) -> str` → summary + description plain text

- [ ] **Step 1: Tests** for string description, ADF doc, empty
- [ ] **Step 2: Implement**
- [ ] **Step 3: pytest — PASS**

---

### Task 3: `fetch` CLI (working product)

**Files:**
- Create: `src/provepr/fetch.py`
- Create: `tests/test_fetch.py`
- Modify: `src/provepr/__main__.py`, `README.md`, `PROJECT.md`, `.env.example`

**Interfaces:**
- `run_fetch(*, repo: str | None, pr: int | None, ticket: str | None) -> int`
- Defaults from `GITHUB_TEST_REPO`, `GITHUB_TEST_PR_NUMBER`, `JIRA_TEST_TICKET`
- Prints: PR title/url, diff size + first ~40 lines, ticket key/summary, PRD preview (~40 lines)
- Exit 0 on success; 1 on missing targets / HTTP errors

- [ ] **Step 1: Tests with fakes**
- [ ] **Step 2: Implement + wire CLI** (`--repo`, `--pr`, `--ticket`)
- [ ] **Step 3: Live** `python -m provepr fetch` against sample PR + real Jira ticket
- [ ] **Step 4: Docs + commit**

**Done when:** `fetch` prints real PR diff + real Jira PRD text for configured targets.

---

## Human inputs for live verify

1. **GitHub:** sample PR on `hmik2003/ProvePR` (agent can create)
2. **Jira:** one readable ticket key → set `JIRA_TEST_TICKET=KEY-123` in `.env`
3. Set `GITHUB_TEST_REPO=hmik2003/ProvePR` and `GITHUB_TEST_PR_NUMBER=<n>`
