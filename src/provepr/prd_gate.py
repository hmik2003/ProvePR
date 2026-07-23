"""PRD quality gate — Story checklist (soft; never blocks merge)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Mandatory sections locked with the team (Story → To Do / sprint).
MANDATORY_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Goals & objectives", ("goal", "objective", "goals & objectives", "goals and objectives")),
    (
        "User / persona context",
        ("persona", "user context", "user / persona", "target user", "who is this for"),
    ),
    ("User stories", ("user stor", "as a ", "user story")),
    (
        "Functional requirements",
        ("functional requirement", "functional req", "requirements:", "must support", "api must"),
    ),
    (
        "Acceptance criteria",
        ("acceptance criteria", "acceptance criterion", "done when", "\nac:", " ac:", "given ", "then "),
    ),
    (
        "Success metrics",
        ("success metric", "kpi", "success metrics", "measurable", "metric:"),
    ),
    (
        "Scope / in-scope",
        ("in-scope", "in scope", "scope:", "scope /", "what's in scope", "what is in scope"),
    ),
)

RECOMMENDED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Out of scope", ("out of scope", "out-of-scope", "non-goals", "not in scope")),
    ("Dependencies", ("dependenc", "assumption", "blocked by")),
    ("Edge cases", ("edge case", "edge-case", "error case")),
    ("Open questions", ("open question", "tbd", "unknown")),
)


@dataclass(frozen=True)
class SectionResult:
    name: str
    present: bool
    evidence: str = ""


@dataclass(frozen=True)
class PrdGateResult:
    ticket_key: str
    issue_type: str
    status: str
    skipped: bool
    skip_reason: str
    verdict: str  # Ready | Needs work | Skipped
    mandatory: tuple[SectionResult, ...]
    recommended: tuple[SectionResult, ...]
    present_count: int
    mandatory_total: int
    subtask_count: int

    @property
    def is_ready(self) -> bool:
        return self.verdict == "Ready"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _find_section(haystack: str, aliases: tuple[str, ...]) -> SectionResult | None:
    for alias in aliases:
        idx = haystack.find(alias)
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(haystack), idx + len(alias) + 60)
            return SectionResult(name="", present=True, evidence=haystack[start:end].strip())
    return None


def score_prd_text(prd_text: str) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    """Heuristic presence check for mandatory + recommended PRD sections."""
    hay = _normalize(prd_text)
    mandatory: list[SectionResult] = []
    for name, aliases in MANDATORY_SECTIONS:
        hit = _find_section(hay, aliases)
        if hit:
            mandatory.append(SectionResult(name=name, present=True, evidence=hit.evidence))
        else:
            mandatory.append(SectionResult(name=name, present=False))

    recommended: list[SectionResult] = []
    for name, aliases in RECOMMENDED_SECTIONS:
        hit = _find_section(hay, aliases)
        if hit:
            recommended.append(SectionResult(name=name, present=True, evidence=hit.evidence))
        else:
            recommended.append(SectionResult(name=name, present=False))
    return tuple(mandatory), tuple(recommended)


def evaluate_prd_gate(
    *,
    ticket_key: str,
    issue_type: str,
    status: str,
    prd_text: str,
    subtask_count: int = 0,
    story_type_names: tuple[str, ...] = ("Story",),
) -> PrdGateResult:
    """
    Soft gate: Story-only. Non-Stories are Skipped (not a failure of the product).
    Ready iff all mandatory sections are detected in Story + subtasks text.
    """
    type_ok = issue_type.strip().lower() in {n.lower() for n in story_type_names}
    if not type_ok:
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=f"Issue type `{issue_type}` is not Story — PRD gate skipped",
            verdict="Skipped",
            mandatory=(),
            recommended=(),
            present_count=0,
            mandatory_total=len(MANDATORY_SECTIONS),
            subtask_count=subtask_count,
        )

    mandatory, recommended = score_prd_text(prd_text)
    present = sum(1 for s in mandatory if s.present)
    total = len(mandatory)
    verdict = "Ready" if present == total else "Needs work"
    return PrdGateResult(
        ticket_key=ticket_key,
        issue_type=issue_type,
        status=status,
        skipped=False,
        skip_reason="",
        verdict=verdict,
        mandatory=mandatory,
        recommended=recommended,
        present_count=present,
        mandatory_total=total,
        subtask_count=subtask_count,
    )


def format_prd_gate_report(result: PrdGateResult) -> str:
    """Human-readable report for CLI / Slack."""
    lines = [
        f"### ProvePR PRD gate — `{result.ticket_key}`",
        f"- Type: {result.issue_type}  |  Status: {result.status}",
        f"- Subtasks included in score: {result.subtask_count}",
    ]
    if result.skipped:
        lines.append(f"- Verdict: **Skipped** — {result.skip_reason}")
        return "\n".join(lines) + "\n"

    lines.append(
        f"- Verdict: **{result.verdict}** "
        f"({result.present_count}/{result.mandatory_total} mandatory sections)"
    )
    lines.append("")
    lines.append("**Mandatory**")
    for section in result.mandatory:
        mark = "OK" if section.present else "MISSING"
        lines.append(f"- [{mark}] {section.name}")

    missing = [s.name for s in result.mandatory if not s.present]
    if missing:
        lines.append("")
        lines.append("**Please add (soft gate — does not block):**")
        for name in missing:
            lines.append(f"- {name}")

    lines.append("")
    lines.append("**Recommended (optional)**")
    for section in result.recommended:
        mark = "OK" if section.present else "—"
        lines.append(f"- [{mark}] {section.name}")

    lines.append("")
    lines.append(
        "_Soft gate: informational only. Ticket stays in To Do — "
        "ProvePR does not move it back to backlog._"
    )
    return "\n".join(lines) + "\n"


def format_prd_gate_slack(result: PrdGateResult) -> str:
    """Short Slack DM for QA lead."""
    if result.skipped:
        return (
            f"ProvePR PRD gate skipped `{result.ticket_key}` "
            f"({result.issue_type}): {result.skip_reason}"
        )
    missing = [s.name for s in result.mandatory if not s.present]
    lines = [
        f"ProvePR PRD gate — {result.ticket_key}",
        f"Verdict: {result.verdict} "
        f"({result.present_count}/{result.mandatory_total} mandatory)",
        f"Status: {result.status} | Type: {result.issue_type}",
    ]
    if missing:
        lines.append("Missing: " + "; ".join(missing))
    else:
        lines.append("All mandatory PRD sections look present.")
    lines.append("Soft gate — ticket was NOT moved back to backlog.")
    lines.append("Jira comment left for PMs on the ticket.")
    return "\n".join(lines)


def _adf_text(text: str) -> dict:
    return {"type": "text", "text": text}


def _adf_paragraph(*parts: str) -> dict:
    content = [_adf_text(p) for p in parts if p is not None]
    return {"type": "paragraph", "content": content or [_adf_text("")]}


def _adf_heading(text: str, level: int = 3) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [_adf_text(text)],
    }


def _adf_bullet(items: list[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [_adf_paragraph(item)],
            }
            for item in items
        ],
    }


def format_prd_gate_jira_adf(result: PrdGateResult) -> dict:
    """Atlassian Document Format body for a PM-facing ticket comment."""
    nodes: list[dict] = [
        _adf_heading("ProvePR PRD quality gate", 2),
        _adf_paragraph(
            f"Ticket: {result.ticket_key}  |  Type: {result.issue_type}  |  "
            f"Status: {result.status}"
        ),
        _adf_paragraph(f"Subtasks included in score: {result.subtask_count}"),
    ]

    if result.skipped:
        nodes.append(_adf_paragraph(f"Verdict: Skipped — {result.skip_reason}"))
        nodes.append(
            _adf_paragraph(
                "Soft gate only. ProvePR never transitions this ticket."
            )
        )
        return {"type": "doc", "version": 1, "content": nodes}

    nodes.append(
        _adf_paragraph(
            f"Verdict: {result.verdict} "
            f"({result.present_count}/{result.mandatory_total} mandatory sections)"
        )
    )
    nodes.append(_adf_heading("Mandatory sections", 3))
    nodes.append(
        _adf_bullet(
            [
                f"{'OK' if s.present else 'MISSING'}: {s.name}"
                for s in result.mandatory
            ]
        )
    )

    missing = [s.name for s in result.mandatory if not s.present]
    if missing:
        nodes.append(_adf_heading("Please add before eng picks this up", 3))
        nodes.append(_adf_bullet(missing))
        nodes.append(
            _adf_paragraph(
                "This is a soft check for PMs/POs. The ticket stays in To Do — "
                "ProvePR does not move it back to backlog."
            )
        )
    else:
        nodes.append(
            _adf_paragraph(
                "All mandatory PRD sections look present. Nice work — "
                "safe for a developer to start against this Story."
            )
        )

    nodes.append(_adf_heading("Recommended (optional)", 3))
    nodes.append(
        _adf_bullet(
            [
                f"{'OK' if s.present else '—'}: {s.name}"
                for s in result.recommended
            ]
        )
    )
    nodes.append(
        _adf_paragraph(
            "Soft gate: informational only. No status change by ProvePR."
        )
    )
    return {"type": "doc", "version": 1, "content": nodes}
