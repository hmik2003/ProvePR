"""Ticket quality gate — Story / Bug / Task / Feature (soft; Spike skipped)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- Story (full PRD) ---
STORY_MANDATORY_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
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

STORY_RECOMMENDED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Out of scope", ("out of scope", "out-of-scope", "non-goals", "not in scope")),
    ("Dependencies", ("dependenc", "assumption", "blocked by")),
    ("Edge cases", ("edge case", "edge-case", "error case")),
    ("Open questions", ("open question", "tbd", "unknown")),
)

# Backward-compatible aliases used by older tests / imports.
MANDATORY_SECTIONS = STORY_MANDATORY_SECTIONS
RECOMMENDED_SECTIONS = STORY_RECOMMENDED_SECTIONS

# --- Bug (QA template bar) ---
BUG_MANDATORY_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Description",
        (
            "description",
            "problem:",
            "issue:",
            "bug:",
            "what's wrong",
            "what is wrong",
            "summary of",
        ),
    ),
    (
        "Steps to reproduce",
        (
            "steps to reproduce",
            "reproduce",
            "reproduction",
            "repro steps",
            "how to reproduce",
            "steps:",
        ),
    ),
    (
        "Expected",
        (
            "expected result",
            "expected behavior",
            "expected:",
            "## expected",
            "expected ",
            "should ",
            "ought to",
        ),
    ),
    (
        "Actual",
        (
            "actual result",
            "actual behavior",
            "actual:",
            "## actual",
            "actual ",
            "instead",
            "currently",
        ),
    ),
    (
        "Environment",
        (
            "environment",
            "env:",
            "browser",
            "os:",
            "device",
            "version:",
            "staging",
            "production",
            "chrome",
            "firefox",
            "safari",
            "android",
            "ios",
        ),
    ),
)

BUG_RECOMMENDED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Attachments / screenshots",
        ("attachment", "screenshot", "screen shot", "see attached", "image", "recording"),
    ),
)

# --- Task (light) ---
TASK_MANDATORY_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Goal",
        ("goal", "objective", "purpose", "what we need", "we need to", "intent"),
    ),
    (
        "Done when",
        (
            "done when",
            "definition of done",
            "acceptance",
            "complete when",
            "finished when",
            "dod",
        ),
    ),
    (
        "Scope / out of scope",
        (
            "out of scope",
            "out-of-scope",
            "in scope",
            "in-scope",
            "scope:",
            "not included",
            "non-goals",
        ),
    ),
)

TASK_RECOMMENDED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = ()

# --- Feature (product increment; larger than a Story, not a research ticket) ---
FEATURE_MANDATORY_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Problem / why",
        (
            "problem",
            "opportunity",
            "why we",
            "why this",
            "background",
            "pain point",
            "the issue",
        ),
    ),
    (
        "Outcome / value",
        (
            "outcome",
            "value",
            "impact",
            "benefit",
            "what success looks",
            "we will enable",
            "users will",
        ),
    ),
    (
        "Scope / in-scope",
        (
            "in-scope",
            "in scope",
            "scope:",
            "scope /",
            "what's in scope",
            "what is in scope",
            "this feature includes",
        ),
    ),
    (
        "Acceptance criteria",
        (
            "acceptance criteria",
            "acceptance criterion",
            "ac:",
            "given ",
            "then ",
            "given/when",
        ),
    ),
    (
        "Success / done when",
        (
            "success metric",
            "success:",
            "kpi",
            "done when",
            "definition of done",
            "how we'll know",
            "how we will know",
            "measurable",
        ),
    ),
)

FEATURE_RECOMMENDED_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Out of scope", ("out of scope", "out-of-scope", "non-goals", "not in scope")),
    ("Dependencies", ("dependenc", "assumption", "blocked by", "child stor", "breakdown")),
    (
        "User / persona",
        ("persona", "target user", "who is this for", "user context"),
    ),
    ("Risks / rollout", ("risk", "rollout", "migration", "feature flag")),
)

STORY_TYPE_NAMES = ("Story", "User Story")
BUG_TYPE_NAMES = ("Bug", "Defect")
TASK_TYPE_NAMES = ("Task",)
FEATURE_TYPE_NAMES = ("Feature", "New Feature")
# Spikes are research tickets — skip for now (same as Epic).
SPIKE_TYPE_NAMES = ("Spike", "Research")
GATED_TYPE_LABEL = "Story/Bug/Task/Feature"

GATE_MARKER = "KodiQA"
GATE_READY_MARKERS = ("Verdict: Ready", "Verdict: **Ready**")
BUG_DESCRIPTION_MIN_CHARS = 120


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
    checklist: str = "story"  # story | bug | task | feature | none
    trigger: str = ""

    @property
    def is_ready(self) -> bool:
        return self.verdict == "Ready"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _type_matches(issue_type: str, names: tuple[str, ...]) -> bool:
    return issue_type.strip().lower() in {n.lower() for n in names}


def _find_section(haystack: str, aliases: tuple[str, ...]) -> SectionResult | None:
    for alias in aliases:
        idx = haystack.find(alias)
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(haystack), idx + len(alias) + 60)
            return SectionResult(name="", present=True, evidence=haystack[start:end].strip())
    return None


def score_sections(
    prd_text: str,
    mandatory_spec: tuple[tuple[str, tuple[str, ...]], ...],
    recommended_spec: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    bug_description_fallback: bool = False,
) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    """Heuristic presence check for a checklist."""
    hay = _normalize(prd_text)
    mandatory: list[SectionResult] = []
    for name, aliases in mandatory_spec:
        hit = _find_section(hay, aliases)
        if (
            not hit
            and bug_description_fallback
            and name == "Description"
            and len(hay) >= BUG_DESCRIPTION_MIN_CHARS
        ):
            mandatory.append(
                SectionResult(
                    name=name,
                    present=True,
                    evidence="(body length qualifies as description)",
                )
            )
        elif hit:
            mandatory.append(SectionResult(name=name, present=True, evidence=hit.evidence))
        else:
            mandatory.append(SectionResult(name=name, present=False))

    recommended: list[SectionResult] = []
    for name, aliases in recommended_spec:
        hit = _find_section(hay, aliases)
        if hit:
            recommended.append(SectionResult(name=name, present=True, evidence=hit.evidence))
        else:
            recommended.append(SectionResult(name=name, present=False))
    return tuple(mandatory), tuple(recommended)


def score_prd_text(prd_text: str) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    """Heuristic presence check for Story mandatory + recommended PRD sections."""
    return score_sections(prd_text, STORY_MANDATORY_SECTIONS, STORY_RECOMMENDED_SECTIONS)


def score_bug_text(prd_text: str) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    return score_sections(
        prd_text,
        BUG_MANDATORY_SECTIONS,
        BUG_RECOMMENDED_SECTIONS,
        bug_description_fallback=True,
    )


def score_task_text(prd_text: str) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    return score_sections(prd_text, TASK_MANDATORY_SECTIONS, TASK_RECOMMENDED_SECTIONS)


def score_feature_text(prd_text: str) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    return score_sections(prd_text, FEATURE_MANDATORY_SECTIONS, FEATURE_RECOMMENDED_SECTIONS)


def prior_gate_was_ready(comment_bodies: list[str]) -> bool:
    """True if a prior KodiQA gate comment already marked Ready (In Progress dedupe)."""
    for body in comment_bodies:
        text = body or ""
        if GATE_MARKER not in text:
            continue
        if any(marker in text for marker in GATE_READY_MARKERS):
            return True
        if "verdict: ready" in text.lower():
            return True
    return False


def prior_gate_comment_exists(comment_bodies: list[str]) -> bool:
    """True if any prior KodiQA gate comment exists (scheduled To Do dedupe)."""
    return any(GATE_MARKER in (body or "") for body in comment_bodies)


def evaluate_prd_gate(
    *,
    ticket_key: str,
    issue_type: str,
    status: str,
    prd_text: str,
    subtask_count: int = 0,
    story_type_names: tuple[str, ...] = STORY_TYPE_NAMES,
    bug_type_names: tuple[str, ...] = BUG_TYPE_NAMES,
    task_type_names: tuple[str, ...] = TASK_TYPE_NAMES,
    feature_type_names: tuple[str, ...] = FEATURE_TYPE_NAMES,
    spike_type_names: tuple[str, ...] = SPIKE_TYPE_NAMES,
    reporter_email: str = "",
    reporter_display_name: str = "",
    bug_skip_reporter_emails: tuple[str, ...] = (),
    skip_reporter_names: tuple[str, ...] = (),
    trigger: str = "",
    prior_ready: bool = False,
    prior_comment: bool = False,
) -> PrdGateResult:
    """
    Soft gate for Story / Bug / Task / Feature. Spike and other types are Skipped.

    Never transitions issues.
    - trigger=in_progress + prior Ready → skip (no double-nag)
    - trigger=to_do + any prior KodiQA comment → skip (scheduled Backlog catch)
    - reporter on skip list (email or display name) → skip all gated types
    """
    trigger_norm = (trigger or "").strip().lower().replace("-", "_")
    if trigger_norm in {"in_progress", "inprogress"} and prior_ready:
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=(
                "In Progress safety net skipped — prior KodiQA gate already Ready"
            ),
            verdict="Skipped",
            mandatory=(),
            recommended=(),
            present_count=0,
            mandatory_total=0,
            subtask_count=subtask_count,
            checklist="none",
            trigger=trigger_norm,
        )
    if trigger_norm in {"to_do", "todo"} and prior_comment:
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=(
                "To Do gate skipped — prior KodiQA comment already exists"
            ),
            verdict="Skipped",
            mandatory=(),
            recommended=(),
            present_count=0,
            mandatory_total=0,
            subtask_count=subtask_count,
            checklist="none",
            trigger=trigger_norm,
        )

    email_skip = {e.strip().lower() for e in bug_skip_reporter_emails if e.strip()}
    name_skip = {n.strip().lower() for n in skip_reporter_names if n.strip()}
    reporter = (reporter_email or "").strip().lower()
    reporter_name = (reporter_display_name or "").strip().lower()
    if (reporter and reporter in email_skip) or (
        reporter_name and reporter_name in name_skip
    ):
        who = reporter_email or reporter_display_name or "(unknown)"
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=(
                f"Reporter `{who}` is on the skip list — gate skipped"
            ),
            verdict="Skipped",
            mandatory=(),
            recommended=(),
            present_count=0,
            mandatory_total=0,
            subtask_count=subtask_count,
            checklist="none",
            trigger=trigger_norm,
        )

    if _type_matches(issue_type, story_type_names):
        checklist = "story"
        mandatory, recommended = score_prd_text(prd_text)
    elif _type_matches(issue_type, bug_type_names):
        checklist = "bug"
        mandatory, recommended = score_bug_text(prd_text)
    elif _type_matches(issue_type, task_type_names):
        checklist = "task"
        mandatory, recommended = score_task_text(prd_text)
    elif _type_matches(issue_type, feature_type_names):
        checklist = "feature"
        mandatory, recommended = score_feature_text(prd_text)
    elif _type_matches(issue_type, spike_type_names):
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=(
                f"Issue type `{issue_type}` (Spike) is not gated yet — skipped"
            ),
            verdict="Skipped",
            mandatory=(),
            recommended=(),
            present_count=0,
            mandatory_total=0,
            subtask_count=subtask_count,
            checklist="none",
            trigger=trigger_norm,
        )
    else:
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=(
                f"Issue type `{issue_type}` is not {GATED_TYPE_LABEL} — gate skipped"
            ),
            verdict="Skipped",
            mandatory=(),
            recommended=(),
            present_count=0,
            mandatory_total=0,
            subtask_count=subtask_count,
            checklist="none",
            trigger=trigger_norm,
        )

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
        checklist=checklist,
        trigger=trigger_norm,
    )


def _audience_label(checklist: str) -> str:
    if checklist == "bug":
        return "reporters / QA"
    if checklist == "task":
        return "creators"
    return "PMs/POs"


def _ticket_noun(checklist: str) -> str:
    return {
        "bug": "Bug",
        "task": "Task",
        "feature": "Feature",
        "story": "Story",
    }.get(checklist, "ticket")


def _gate_title(checklist: str) -> str:
    return {
        "bug": "Bug quality gate",
        "task": "Task quality gate",
        "feature": "Feature quality gate",
        "story": "PRD gate",
    }.get(checklist, "quality gate")


def _slack_label(checklist: str) -> str:
    return {
        "bug": "Bug gate",
        "task": "Task gate",
        "feature": "Feature gate",
        "story": "PRD gate",
    }.get(checklist, "gate")


def _jira_heading(checklist: str) -> str:
    return {
        "bug": "KodiQA Bug quality gate",
        "task": "KodiQA Task quality gate",
        "feature": "KodiQA Feature quality gate",
        "story": "KodiQA PRD quality gate",
    }.get(checklist, "KodiQA quality gate")


def format_prd_gate_report(result: PrdGateResult) -> str:
    """Human-readable report for CLI / Slack."""
    title = _gate_title(result.checklist)
    lines = [
        f"### KodiQA {title} — `{result.ticket_key}`",
        f"- Type: {result.issue_type}  |  Status: {result.status}",
        f"- Subtasks included in score: {result.subtask_count}",
    ]
    if result.trigger:
        lines.append(f"- Trigger: {result.trigger}")
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
        lines.append("**Please add before In Progress (soft gate — does not block):**")
        for name in missing:
            lines.append(f"- {name}")

    if result.recommended:
        lines.append("")
        lines.append("**Recommended (optional)**")
        for section in result.recommended:
            mark = "OK" if section.present else "—"
            lines.append(f"- [{mark}] {section.name}")

    lines.append("")
    lines.append(
        "_Soft gate: informational only. Ticket status is unchanged — "
        "KodiQA does not move it back to backlog._"
    )
    return "\n".join(lines) + "\n"


def format_prd_gate_slack(result: PrdGateResult) -> str:
    """Short Slack DM for QA lead."""
    label = _slack_label(result.checklist)
    if result.skipped:
        return (
            f"KodiQA {label} skipped `{result.ticket_key}` "
            f"({result.issue_type}): {result.skip_reason}"
        )
    missing = [s.name for s in result.mandatory if not s.present]
    lines = [
        f"KodiQA {label} — {result.ticket_key}",
        f"Verdict: {result.verdict} "
        f"({result.present_count}/{result.mandatory_total} mandatory)",
        f"Status: {result.status} | Type: {result.issue_type}",
    ]
    if result.trigger:
        lines.append(f"Trigger: {result.trigger}")
    if missing:
        lines.append("Missing: " + "; ".join(missing))
        lines.append("Please revise before a dev moves this to In Progress.")
    else:
        lines.append("All mandatory sections look present.")
    lines.append("Soft gate — ticket status was NOT changed.")
    lines.append(f"Jira comment left for {_audience_label(result.checklist)}.")
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
    """Atlassian Document Format body for a creator-facing ticket comment."""
    heading = _jira_heading(result.checklist)

    nodes: list[dict] = [
        _adf_heading(heading, 2),
        _adf_paragraph(
            f"Ticket: {result.ticket_key}  |  Type: {result.issue_type}  |  "
            f"Status: {result.status}"
        ),
        _adf_paragraph(f"Subtasks included in score: {result.subtask_count}"),
    ]
    if result.trigger:
        nodes.append(_adf_paragraph(f"Trigger: {result.trigger}"))

    if result.skipped:
        nodes.append(_adf_paragraph(f"Verdict: Skipped — {result.skip_reason}"))
        nodes.append(
            _adf_paragraph("Soft gate only. KodiQA never transitions this ticket.")
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
            [f"{'OK' if s.present else 'MISSING'}: {s.name}" for s in result.mandatory]
        )
    )

    missing = [s.name for s in result.mandatory if not s.present]
    noun = _ticket_noun(result.checklist)
    if missing:
        nodes.append(_adf_heading("Please add before In Progress", 3))
        nodes.append(_adf_bullet(missing))
        nodes.append(
            _adf_paragraph(
                f"This is a soft check for {_audience_label(result.checklist)}. "
                f"Revise this {noun} before a developer moves it to In Progress. "
                "KodiQA does not change ticket status."
            )
        )
    else:
        nodes.append(
            _adf_paragraph(
                f"All mandatory sections look present. Nice work — "
                f"safe for a developer to start against this {noun}."
            )
        )

    if result.recommended:
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
        _adf_paragraph("Soft gate: informational only. No status change by KodiQA.")
    )
    return {"type": "doc", "version": 1, "content": nodes}
