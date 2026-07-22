# Sprint 6 — HTTP Trigger Implementation Plan

> **Goal:** Expose `POST /v1/review` so GitHub Actions (Sprint 7) can trigger ProvePR without the CLI.

**Done when:** `python -m provepr serve` listens locally; `/health` works; authenticated `/v1/review` invokes `run_review(yes=True)`.

**Auth:** `Authorization: Bearer $PROVEPR_TRIGGER_SECRET`

**Cost:** Each POST spends one Gemini call (same as `--yes`).
