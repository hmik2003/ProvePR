"""Read-only GitHub REST helpers for ProvePR."""

from __future__ import annotations

import httpx

from provepr.config import GitHubSettings

API_ROOT = "https://api.github.com"


class GitHubClient:
    def __init__(
        self,
        settings: GitHubSettings,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=API_ROOT,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {settings.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ProvePR",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_authenticated_user(self) -> dict:
        response = self._client.get("/user")
        response.raise_for_status()
        return response.json()

    def get_repo(self, full_name: str) -> dict:
        response = self._client.get(f"/repos/{full_name}")
        response.raise_for_status()
        return response.json()
