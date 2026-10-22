"""GitHub REST helpers for ProvePR (read PR/diff; write PR comments only)."""

from __future__ import annotations

import httpx

from provepr.config import GitHubSettings

API_ROOT = "https://api.github.com"


class GitHubClient:
    """Fetch PRs/diffs and optionally post review comments. No code push/merge APIs."""
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
                "User-Agent": "KodiQA",
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

    def get_pull_request(self, full_name: str, number: int) -> dict:
        response = self._client.get(f"/repos/{full_name}/pulls/{number}")
        response.raise_for_status()
        return response.json()

    def get_pull_request_diff(self, full_name: str, number: int) -> str:
        """
        Return unified diff text for a PR.

        Prefer the pull diff media type. If that returns 403 (common when the
        App lacks Contents: Read), fall back to concatenating per-file patches
        from GET /pulls/{n}/files (works with Pull requests: Read alone).
        """
        response = self._client.get(
            f"/repos/{full_name}/pulls/{number}",
            headers={"Accept": "application/vnd.github.diff"},
        )
        if response.status_code == 403:
            return self._diff_from_pull_files(full_name, number)
        response.raise_for_status()
        return response.text

    def _diff_from_pull_files(self, full_name: str, number: int) -> str:
        chunks: list[str] = []
        page = 1
        while True:
            response = self._client.get(
                f"/repos/{full_name}/pulls/{number}/files",
                params={"per_page": 100, "page": page},
            )
            response.raise_for_status()
            files = response.json()
            if not isinstance(files, list) or not files:
                break
            for item in files:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename") or "file"
                status = item.get("status") or "modified"
                patch = item.get("patch")
                chunks.append(f"--- a/{filename} ({status})")
                chunks.append(f"+++ b/{filename}")
                if isinstance(patch, str) and patch.strip():
                    chunks.append(patch)
                else:
                    chunks.append("(binary or empty patch)")
                chunks.append("")
            if len(files) < 100:
                break
            page += 1
        if not chunks:
            raise httpx.HTTPStatusError(
                "PR files returned no patches",
                request=response.request,
                response=response,
            )
        return "\n".join(chunks)

    def create_issue_comment(self, full_name: str, number: int, body: str) -> dict:
        """Post a comment on a PR (issues comments API). Needs Pull requests: Write."""
        response = self._client.post(
            f"/repos/{full_name}/issues/{number}/comments",
            json={"body": body},
        )
        response.raise_for_status()
        return response.json()
