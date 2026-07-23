"""Sprint 6 — HTTP trigger for ProvePR reviews + PRD gate."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from provepr.config import load_env
from provepr.prd_gate_cli import execute_prd_gate
from provepr.review import run_review

app = FastAPI(title="ProvePR", version="0.1.0")


class ReviewRequest(BaseModel):
    repo: str | None = None
    pr: int | None = None
    ticket: str | None = None
    post: bool = False


class ReviewResponse(BaseModel):
    ok: bool
    exit_code: int
    detail: str


class PrdGateRequest(BaseModel):
    """CLI-style body or loose Jira Automation webhook fields."""

    ticket: str | None = None
    issue: dict[str, Any] | None = None
    comment: bool = True
    notify: bool = True


class PrdGateResponse(BaseModel):
    ok: bool
    ticket_key: str = ""
    verdict: str = ""
    skipped: bool = False
    detail: str = ""
    jira_commented: bool = False


def _expected_secret() -> str:
    load_env()
    return (os.getenv("PROVEPR_TRIGGER_SECRET") or "").strip()


def _authorize(authorization: str | None) -> None:
    expected = _expected_secret()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="PROVEPR_TRIGGER_SECRET is not configured on the server",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid token")


def _ticket_from_prd_gate_body(body: PrdGateRequest) -> str:
    if body.ticket and str(body.ticket).strip():
        return str(body.ticket).strip()
    if isinstance(body.issue, dict):
        key = body.issue.get("key")
        if key:
            return str(key).strip()
    raise HTTPException(
        status_code=422,
        detail="Provide ticket (e.g. PROV-10) or issue.key from Jira Automation",
    )


@app.get("/health")
def health() -> dict[str, str]:
    from provepr import __version__
    from provepr.hermes_review import hermes_available

    return {
        "status": "ok",
        "service": "provepr",
        "version": __version__,
        "engine": "hermes" if hermes_available() else "single-shot-fallback",
    }


@app.post("/v1/review", response_model=ReviewResponse)
def trigger_review(
    body: ReviewRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> ReviewResponse:
    """
    Run a Hermes+Gemini review (or single-shot fallback).
    Always spends model budget when invoked. Set post=true to also comment on GitHub (+ Slack).
    """
    _authorize(authorization)
    code = run_review(
        repo=body.repo,
        pr=body.pr,
        ticket=body.ticket,
        yes=True,
        post=body.post,
    )
    if code != 0:
        return ReviewResponse(
            ok=False,
            exit_code=code,
            detail="Review failed — check server logs / env targets",
        )
    return ReviewResponse(
        ok=True,
        exit_code=0,
        detail="Review completed" + (" and published" if body.post else ""),
    )


@app.post("/v1/prd-gate", response_model=PrdGateResponse)
def trigger_prd_gate(
    body: PrdGateRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> PrdGateResponse:
    """
    Soft Story PRD quality gate for Jira Automation (Story → To Do).

    Leaves a Jira comment for PMs + Slack DM for QA. Never transitions the ticket.
    """
    _authorize(authorization)
    ticket = _ticket_from_prd_gate_body(body)
    try:
        run = execute_prd_gate(
            ticket=ticket,
            comment=body.comment,
            notify=body.notify,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface cleanly to caller
        raise HTTPException(
            status_code=502,
            detail=f"PRD gate failed: {exc.__class__.__name__}: {exc}",
        ) from exc

    result = run.result
    return PrdGateResponse(
        ok=True,
        ticket_key=result.ticket_key,
        verdict=result.verdict,
        skipped=result.skipped,
        detail=result.skip_reason or f"{result.present_count}/{result.mandatory_total}",
        jira_commented=bool(run.jira_comment_url)
        or (body.comment and not result.skipped),
    )


def run_server() -> int:
    """Start uvicorn. Cloud Run uses PORT; local uses PROVEPR_HTTP_*."""
    load_env()
    host = (
        os.getenv("PROVEPR_HTTP_HOST")
        or os.getenv("HOST")
        or ("0.0.0.0" if os.getenv("PORT") else "127.0.0.1")
    ).strip()
    port_raw = (
        os.getenv("PORT")
        or os.getenv("PROVEPR_HTTP_PORT")
        or "8080"
    ).strip()
    try:
        port = int(port_raw)
    except ValueError:
        print(f"Serve FAIL: invalid port={port_raw!r}")
        return 1

    if not _expected_secret():
        print("Serve FAIL: set PROVEPR_TRIGGER_SECRET in .env before serving")
        return 1

    import uvicorn

    print("=== ProvePR — HTTP serve ===")
    print(f"Listening on http://{host}:{port}")
    print(
        "Endpoints: GET /health  POST /v1/review  POST /v1/prd-gate "
        "(Bearer PROVEPR_TRIGGER_SECRET)"
    )
    print("Each POST /v1/review runs Hermes+Gemini (capped) or single-shot fallback.")
    print(
        "POST /v1/prd-gate = soft Story PRD check "
        "(Jira comment + Slack; no transitions)."
    )
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
