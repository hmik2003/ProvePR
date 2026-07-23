"""Jira Development panel helpers (non-blocking PR link check)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DevelopmentLinkCheck:
    """Result of comparing a GitHub PR to Jira Development panel data."""

    status: str  # linked | not_linked | unavailable
    message: str
    linked_pr_urls: tuple[str, ...] = ()

    @property
    def is_linked(self) -> bool:
        return self.status == "linked"


def check_pr_linked_in_development(
    *,
    pr_number: int,
    pr_html_url: str | None,
    pull_requests: list[dict],
) -> DevelopmentLinkCheck:
    """
    Non-blocking check: is this GitHub PR visible on the Jira Development panel?

    Matching is best-effort on PR number and/or URL substring.
    Empty pull_requests with no error is treated as not_linked.
    """
    urls: list[str] = []
    matched = False
    needle_url = (pr_html_url or "").strip().rstrip("/").lower()
    for pr in pull_requests:
        url = str(pr.get("url") or pr.get("html_url") or "").strip()
        if url:
            urls.append(url)
        num = pr.get("id") or pr.get("number") or pr.get("displayId")
        try:
            if num is not None and int(str(num).lstrip("#")) == int(pr_number):
                matched = True
        except (TypeError, ValueError):
            pass
        if needle_url and url and needle_url in url.rstrip("/").lower():
            matched = True
        # Some payloads nest name like "#12" or "Pull request #12"
        name = str(pr.get("name") or pr.get("title") or "")
        if f"#{pr_number}" in name.replace(" ", ""):
            matched = True

    if matched:
        return DevelopmentLinkCheck(
            status="linked",
            message=(
                f"This PR appears on the Jira Development panel "
                f"(matched #{pr_number})."
            ),
            linked_pr_urls=tuple(urls),
        )

    return DevelopmentLinkCheck(
        status="not_linked",
        message=(
            f"This PR (#{pr_number}) was **not** found on the ticket's "
            f"**Development** panel in Jira. Please link the branch/PR to the "
            f"ticket (GitHub for Jira / smart commits / Development panel) so "
            f"traceability stays clear. This does **not** block the review."
        ),
        linked_pr_urls=tuple(urls),
    )


def format_development_advisory(check: DevelopmentLinkCheck) -> str:
    """Markdown block for the ProvePR GitHub comment (advisory only)."""
    if check.status == "linked":
        return (
            "### Development panel\n"
            f"- Status: **Linked** — {check.message}\n"
        )
    if check.status == "unavailable":
        return (
            "### Development panel\n"
            f"- Status: **Could not verify** — {check.message}\n"
            "- Action: If your site uses GitHub for Jira, please confirm the PR "
            "shows under the ticket's Development section. Not a merge blocker.\n"
        )
    return (
        "### Development panel\n"
        f"- Status: **Not linked** — {check.message}\n"
        "- Action (please): Link this PR/branch on the Jira ticket Development "
        "section. **Non-blocking** — review still proceeds.\n"
    )
