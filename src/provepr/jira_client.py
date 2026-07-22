"""Read-only Jira Cloud REST helpers for ProvePR."""

from __future__ import annotations

import httpx

from provepr.config import JiraSettings


class JiraClient:
    def __init__(
        self,
        settings: JiraSettings,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=settings.server_url,
            auth=(settings.email, settings.api_token),
            headers={
                "Accept": "application/json",
                "User-Agent": "ProvePR",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JiraClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_myself(self) -> dict:
        response = self._client.get("/rest/api/3/myself")
        response.raise_for_status()
        return response.json()

    def get_issue(self, key: str) -> dict:
        response = self._client.get(f"/rest/api/3/issue/{key}")
        response.raise_for_status()
        return response.json()
