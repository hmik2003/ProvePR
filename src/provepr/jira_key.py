"""Extract Jira issue keys from PR title / branch / body."""

from __future__ import annotations

import re

# PROJ-123, SX-2869, etc.
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def extract_jira_key(*texts: str | None) -> str | None:
    """Return the first Jira key found, searching texts in order."""
    for text in texts:
        if not text:
            continue
        match = JIRA_KEY_RE.search(text)
        if match:
            return match.group(1)
    return None
