"""Mint a short-lived GitHub App installation token (posts as the App, e.g. KodiQA[bot])."""

from __future__ import annotations

import time
from typing import Any

import httpx

API_ROOT = "https://api.github.com"


def normalize_private_key(pem: str) -> str:
    """Accept .env-friendly keys where newlines are stored as \\n."""
    key = (pem or "").strip()
    if "\\n" in key and "\n" not in key:
        key = key.replace("\\n", "\n")
    return key


def build_app_jwt(*, app_id: str, private_key_pem: str, now: int | None = None) -> str:
    try:
        import jwt  # PyJWT
    except ImportError as exc:  # pragma: no cover
        raise ValueError(
            "PyJWT is required for GitHub App auth — pip install PyJWT cryptography"
        ) from exc

    ts = int(time.time() if now is None else now)
    payload = {
        "iat": ts - 60,
        "exp": ts + (9 * 60),
        "iss": str(app_id).strip(),
    }
    token = jwt.encode(
        payload,
        normalize_private_key(private_key_pem),
        algorithm="RS256",
    )
    if isinstance(token, bytes):
        return token.decode("ascii")
    return token


def create_installation_access_token(
    *,
    app_id: str,
    private_key_pem: str,
    installation_id: str,
    client: httpx.Client | None = None,
) -> str:
    """
    Exchange App credentials for an installation token.
    Comments made with this token appear as <AppSlug>[bot] (e.g. KodiQA[bot]).
    """
    owns = client is None
    jwt_token = build_app_jwt(app_id=app_id, private_key_pem=private_key_pem)
    http = client or httpx.Client(
        base_url=API_ROOT,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {jwt_token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "KodiQA",
        },
        timeout=30.0,
    )
    try:
        response = http.post(
            f"/app/installations/{str(installation_id).strip()}/access_tokens",
            json={},
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        token = (data.get("token") or "").strip()
        if not token:
            raise ValueError("GitHub App installation token response missing token")
        return token
    finally:
        if owns:
            http.close()
