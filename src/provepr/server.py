"""Sprint 6 — HTTP trigger for ProvePR reviews."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from provepr.config import load_env
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "provepr"}


@app.post("/v1/review", response_model=ReviewResponse)
def trigger_review(
    body: ReviewRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> ReviewResponse:
    """
    Run one Gemini review (always spends one model call).
    Set post=true to also comment on GitHub (+ Slack DM if configured).
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


def run_server() -> int:
    """Start uvicorn using PROVEPR_HTTP_HOST / PROVEPR_HTTP_PORT."""
    load_env()
    host = (os.getenv("PROVEPR_HTTP_HOST") or "127.0.0.1").strip()
    port_raw = (os.getenv("PROVEPR_HTTP_PORT") or "8080").strip()
    try:
        port = int(port_raw)
    except ValueError:
        print(f"Serve FAIL: invalid PROVEPR_HTTP_PORT={port_raw!r}")
        return 1

    if not _expected_secret():
        print("Serve FAIL: set PROVEPR_TRIGGER_SECRET in .env before serving")
        return 1

    import uvicorn

    print("=== ProvePR — Sprint 6 HTTP ===")
    print(f"Listening on http://{host}:{port}")
    print("Endpoints: GET /health  POST /v1/review (Bearer PROVEPR_TRIGGER_SECRET)")
    print("Each POST /v1/review spends exactly one Gemini call.")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
