"""Extract plain-text PRD / requirements from Jira issue payloads."""

from __future__ import annotations


def adf_to_text(node: object) -> str:
    """Flatten Atlassian Document Format (or nested dict/list) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        parts = [adf_to_text(item) for item in node]
        return "".join(parts)
    if isinstance(node, dict):
        node_type = node.get("type")
        if node_type == "text":
            return str(node.get("text") or "")
        if node_type == "hardBreak":
            return "\n"
        content = node.get("content")
        inner = adf_to_text(content) if content is not None else ""
        if node_type in {"paragraph", "heading", "blockquote", "listItem", "codeBlock"}:
            return inner + "\n"
        if node_type in {"bulletList", "orderedList"}:
            return inner
        return inner
    return str(node)


def issue_prd_text(issue: dict) -> str:
    """Build a requirements blob from issue summary + description."""
    fields = issue.get("fields") or {}
    summary = (fields.get("summary") or "").strip()
    description = fields.get("description")
    if isinstance(description, str):
        body = description.strip()
    else:
        body = adf_to_text(description).strip()

    parts: list[str] = []
    if summary:
        parts.append(f"Summary: {summary}")
    if body:
        parts.append(body)
    return "\n\n".join(parts).strip()


def build_prd_with_subtasks(parent: dict, subtasks: list[dict]) -> str:
    """Parent PRD plus clearly labeled subtask sections (for thin parents)."""
    parts: list[str] = []
    parent_key = str(parent.get("key") or "")
    parent_block = issue_prd_text(parent)
    if parent_block:
        header = f"## Parent ticket {parent_key}".strip()
        parts.append(f"{header}\n\n{parent_block}" if parent_key else parent_block)

    for child in subtasks:
        child_key = str(child.get("key") or "?")
        child_fields = child.get("fields") or {}
        status = ""
        st = child_fields.get("status")
        if isinstance(st, dict):
            status = str(st.get("name") or "")
        status_bit = f" ({status})" if status else ""
        child_block = issue_prd_text(child)
        if not child_block:
            continue
        parts.append(f"## Subtask {child_key}{status_bit}\n\n{child_block}")

    return "\n\n".join(parts).strip()
