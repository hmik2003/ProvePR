"""Extract Jira issue keys from PR title / branch / body."""

from __future__ import annotations

import re

# PROJ-123, SX-2869, etc.
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def extract_jira_keys(text: str | None) -> list[str]:
    """Return unique Jira keys in order of first appearance."""
    if not text:
        return []
    seen: set[str] = set()
    keys: list[str] = []
    for match in JIRA_KEY_RE.finditer(text):
        key = match.group(1)
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


def extract_jira_key(*texts: str | None) -> str | None:
    """Return the first Jira key found, searching texts in order."""
    for text in texts:
        keys = extract_jira_keys(text)
        if keys:
            return keys[0]
    return None


def primary_jira_key_from_title(title: str | None) -> tuple[str | None, list[str]]:
    """
    Company policy: exactly one Jira key in the PR title.
    Returns (primary_or_none, all_keys_in_title).
    """
    keys = extract_jira_keys(title)
    if len(keys) == 1:
        return keys[0], keys
    return None, keys
