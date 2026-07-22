# Sprint 1 — Project Scaffold Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox syntax.

**Goal:** Deliver a runnable local project that validates environment setup without needing live API keys yet.

**Architecture:** Small Python package `provepr` with a `smoke` CLI. Secrets stay in `.env` (gitignored). `PROJECT.md` remains the living product context.

**Tech Stack:** Python 3.11+, `python-dotenv`, `pytest`

## Global Constraints

- Never commit `.env` or real secrets
- Hermes + Gemini locked for later sprints; Sprint 1 does not install Hermes yet
- Personal GitHub (`hmik2003`) first; company pilots later
- Product name is **ProvePR** (tagline: ProvePR — AI PR Reviewer)
- One working product increment per sprint

---

### Task 1: Scaffold + smoke CLI

**Files:**
- Create: `.gitignore`, `.env.example`, `requirements.txt`, `README.md`
- Create: `src/provepr/__init__.py`, `__main__.py`, `config.py`, `smoke.py`
- Create: `tests/test_config.py`
- Modify: `PROJECT.md` (phase status)

- [x] **Step 1:** Add ignore rules, env template, requirements
- [x] **Step 2:** Implement config loader (presence checks only; never print secret values)
- [x] **Step 3:** Implement `python -m provepr smoke`
- [x] **Step 4:** Add pytest for config key listing
- [x] **Step 5:** Create venv, install deps, run smoke + tests
- [x] **Step 6:** Commit Sprint 1
- [x] **Step 7:** Final product rename to ProvePR (`provepr` package + folder)

**Done when:** `smoke` exits successfully and prints a clear “Sprint 1 OK” plus next-key checklist.
