"""HTTP triggers: review, PR hook, skip-notify, PRD gate."""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from provepr.config import load_env
from provepr.pr_hook import decide_pr_ticket
from provepr.prd_gate_cli import execute_prd_gate
from provepr.review import run_review
from provepr.skip_notify import run_skip_notify

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


class SkipNotifyRequest(BaseModel):
    repo: str
    pr: int
    reason: str = "none"
    title: str = ""
    pr_url: str = ""
    detail: str = ""
    comment: bool = True


class SkipNotifyResponse(BaseModel):
    ok: bool
    exit_code: int
    detail: str


class PrHookRequest(BaseModel):
    """Thin GitHub Action payload — Cloud Run decides review vs skip."""

    repo: str
    pr: int
    title: str = ""
    body: str = ""
    branch: str = ""
    pr_url: str = ""
    post: bool = True


class PrHookResponse(BaseModel):
    ok: bool
    action: str = ""  # review | skip
    ticket_key: str = ""
    exit_code: int = 0
    detail: str = ""


class PrdGateRequest(BaseModel):
    """CLI-style body or loose Jira Automation webhook fields."""

    ticket: str | None = None
    issue: dict[str, Any] | None = None
    comment: bool = True
    notify: bool = True
    # to_do | in_progress | manual — in_progress skips if prior gate already Ready
    trigger: str | None = None


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
    Soft Story / Bug / Task / Feature quality gate for Jira Automation.

    Leaves a Jira comment + Slack DM for QA. Never transitions the ticket.
    Pass trigger=in_progress for delayed types (Bug/Task) to dedupe Ready.
    Spike tickets are skipped for now.
    """
    _authorize(authorization)
    ticket = _ticket_from_prd_gate_body(body)
    try:
        run = execute_prd_gate(
            ticket=ticket,
            comment=body.comment,
            notify=body.notify,
            trigger=(body.trigger or ""),
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


@app.post("/v1/skip-notify", response_model=SkipNotifyResponse)
def trigger_skip_notify(
    body: SkipNotifyRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> SkipNotifyResponse:
    """Slack + optional PR comment when a review is skipped (no Gemini)."""
    _authorize(authorization)
    code = run_skip_notify(
        repo=body.repo,
        pr=body.pr,
        reason=body.reason,
        title=body.title,
        pr_url=body.pr_url,
        detail=body.detail,
        comment=body.comment,
    )
    return SkipNotifyResponse(
        ok=code == 0,
        exit_code=code,
        detail="Skip notify completed" if code == 0 else "Skip notify failed",
    )


@app.post("/v1/pr-hook", response_model=PrHookResponse)
def trigger_pr_hook(
    body: PrHookRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> PrHookResponse:
    """
    Thin multi-repo entrypoint: extract Jira key → review or skip-notify.

    GitHub Actions only need PROVEPR_URL + PROVEPR_TRIGGER_SECRET.
    """
    _authorize(authorization)
    if not body.repo or "/" not in body.repo:
        raise HTTPException(status_code=422, detail="repo owner/name is required")
    if body.pr < 1:
        raise HTTPException(status_code=422, detail="pr must be a positive integer")

    decision = decide_pr_ticket(
        title=body.title, branch=body.branch, body=body.body
    )
    if decision.action == "skip":
        code = run_skip_notify(
            repo=body.repo,
            pr=body.pr,
            reason=decision.skip_reason or "none",
            title=body.title,
            pr_url=body.pr_url,
            detail=decision.skip_detail,
            comment=True,
        )
        return PrHookResponse(
            ok=code == 0,
            action="skip",
            ticket_key="",
            exit_code=code,
            detail=(
                f"Skipped ({decision.skip_reason}"
                + (f": {decision.skip_detail}" if decision.skip_detail else "")
                + ")"
            ),
        )

    code = run_review(
        repo=body.repo,
        pr=body.pr,
        ticket=decision.ticket,
        yes=True,
        post=body.post,
    )
    return PrHookResponse(
        ok=code == 0,
        action="review",
        ticket_key=decision.ticket,
        exit_code=code,
        detail=(
            f"Review via {decision.source}"
            + (" published" if body.post and code == 0 else "")
        ),
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
        "Endpoints: GET /health  POST /v1/pr-hook  POST /v1/review  "
        "POST /v1/skip-notify  POST /v1/prd-gate "
        "(Bearer PROVEPR_TRIGGER_SECRET)"
    )
    print("Thin Actions: POST /v1/pr-hook (review or skip).")
    print("PM Automation: POST /v1/prd-gate (Story/Bug/Task/Feature soft gate).")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
