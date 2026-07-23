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

    def get_issue(self, key: str, *, fields: str | None = None) -> dict:
        params = {}
        if fields:
            params["fields"] = fields
        response = self._client.get(f"/rest/api/3/issue/{key}", params=params or None)
        response.raise_for_status()
        return response.json()

    def get_subtasks(self, parent_key: str) -> list[dict]:
        """Return full issue payloads for subtasks of parent_key (empty if none)."""
        parent = self.get_issue(parent_key, fields="summary,subtasks")
        fields = parent.get("fields") or {}
        stubs = fields.get("subtasks") or []
        children: list[dict] = []
        for stub in stubs:
            child_key = stub.get("key")
            if not child_key:
                continue
            try:
                children.append(
                    self.get_issue(str(child_key), fields="summary,description,status")
                )
            except httpx.HTTPStatusError:
                continue
        return children

    def get_development_pull_requests(self, issue: dict) -> tuple[list[dict], str | None]:
        """
        Best-effort read of PRs on the Jira Development panel.

        Returns (pull_requests, error_message).
        Uses undocumented /rest/dev-status endpoints; may fail without
        View Development Tools permission or GitHub-for-Jira.
        """
        issue_id = issue.get("id")
        if not issue_id:
            return [], "Issue id missing; cannot query Development panel"

        # Try GitHub-oriented detail first, then generic summary.
        detail_urls = [
            (
                "/rest/dev-status/latest/issue/detail",
                {
                    "issueId": str(issue_id),
                    "applicationType": "GitHub",
                    "dataType": "pullrequest",
                },
            ),
            (
                "/rest/dev-status/1.0/issue/detail",
                {
                    "issueId": str(issue_id),
                    "applicationType": "GitHub",
                    "dataType": "pullrequest",
                },
            ),
            (
                "/rest/dev-status/latest/issue/detail",
                {
                    "issueId": str(issue_id),
                    "applicationType": "github",
                    "dataType": "pullrequest",
                },
            ),
        ]

        last_err: str | None = None
        for path, params in detail_urls:
            try:
                response = self._client.get(path, params=params)
                if response.status_code in {401, 403}:
                    return [], (
                        "No permission to read Development panel "
                        "(needs View Development Tools), or integration unavailable"
                    )
                if response.status_code == 404:
                    last_err = "Development panel API not found on this Jira site"
                    continue
                response.raise_for_status()
                data = response.json()
                prs = _extract_pull_requests(data)
                return prs, None
            except httpx.HTTPStatusError as exc:
                last_err = f"HTTP {exc.response.status_code} reading Development panel"
            except httpx.RequestError as exc:
                last_err = f"Request error reading Development panel ({exc.__class__.__name__})"

        # Fallback summary endpoint (counts only — treat as unavailable for matching)
        try:
            response = self._client.get(
                "/rest/dev-status/latest/issue/summary",
                params={"issueId": str(issue_id)},
            )
            if response.status_code in {401, 403}:
                return [], (
                    "No permission to read Development panel "
                    "(needs View Development Tools)"
                )
            if response.is_success:
                # Summary alone cannot prove this PR number — mark unavailable for match
                return [], (
                    "Development summary available but PR detail could not be loaded; "
                    "please confirm the link manually"
                )
        except httpx.HTTPError:
            pass

        return [], last_err or "Could not read Development panel"


def _extract_pull_requests(payload: object) -> list[dict]:
    """Normalize nested dev-status payloads into a flat list of PR dicts."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if "pullRequests" in node and isinstance(node["pullRequests"], list):
            for pr in node["pullRequests"]:
                if isinstance(pr, dict):
                    found.append(pr)
        # Some shapes use pullrequest singular lists under detail
        for key, value in node.items():
            if key in {"pullRequests", "detail", "errors", "_instance"}:
                walk(value)
            elif isinstance(value, (dict, list)) and key not in {
                "repository",
                "author",
                "lastCommit",
            }:
                walk(value)

    walk(payload)
    return found
