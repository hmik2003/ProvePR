"""Ticket quality gate — Story / Bug / Task / Feature (soft; Spike skipped)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- Story (full PRD) ---
STORY_MANDATORY_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Goals & objectives",
        (
            "goal",
            "goals",
            "objective",
            "objectives",
            "goals & objectives",
            "goals and objectives",
            "what",
            "purpose",
            "intent",
        ),
    ),
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
        (
            "acceptance criteria",
            "acceptance criterion",
            "done when",
            "done",
            "\nac:",
            " ac:",
            "given ",
            "then ",
        ),
    ),
    (
        "Success metrics",
        ("success metric", "kpi", "success metrics", "measurable", "metric:"),
    ),
    (
        "Scope / in-scope",
        (
            "in-scope",
            "in scope",
            "scope:",
            "scope /",
            "scope",
            "what's in scope",
            "what is in scope",
            "what's included",
            "what is included",
        ),
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
        (
            "goal",
            "goals",
            "objective",
            "objectives",
            "purpose",
            "intent",
            "what",
            "overview",
            "context",
            "background",
            "problem",
            "what we need",
            "we need to",
            "the aim",
        ),
    ),
    (
        "Done when",
        (
            "done when",
            "done",
            "definition of done",
            "acceptance",
            "acceptance criteria",
            "complete when",
            "finished when",
            "dod",
            "deliverable",
            "deliverables",
            "success criteria",
            "completion",
            "exit criteria",
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
            "scope",
            "not included",
            "non-goals",
            "non goals",
            "what's included",
            "what is included",
            "boundaries",
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
            "why",
            "background",
            "pain point",
            "the issue",
            "what",
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
            "scope",
            "what's in scope",
            "what is in scope",
            "this feature includes",
            "what's included",
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
            "success",
            "kpi",
            "done when",
            "done",
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


# Short / ambiguous aliases only count as section headings, not body substrings.
_HEADING_ONLY_ALIASES = frozenset(
    {
        "what",
        "done",
        "why",
        "goal",
        "goals",
        "scope",
        "success",
        "problem",
        "context",
        "overview",
        "background",
        "intent",
        "purpose",
        "outcome",
        "value",
        "ac",
        "dod",
        "who",
    }
)

_STOPWORDS = frozenset(
    {"a", "an", "the", "and", "or", "of", "to", "for", "on", "in", "vs", "via"}
)

_SECTION_BODY_MIN_CHARS = 20


def _normalize_label(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s/&+-]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _strip_heading_markup(line: str) -> str:
    text = (line or "").strip()
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^\*\*(.+)\*\*$", r"\1", text)
    text = re.sub(r"^__(.+)__$", r"\1", text)
    text = re.sub(r"^\*(.+)\*$", r"\1", text)
    return text.strip().rstrip(":").strip()


def _is_title_case_label(text: str) -> bool:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'/-]*", text)
    if not words or len(words) > 8:
        return False
    for word in words:
        lower = word.lower()
        if lower in _STOPWORDS:
            continue
        if not word[0].isupper():
            return False
    return True


def _is_probable_heading(line: str) -> bool:
    raw = (line or "").strip()
    if not raw or len(raw) > 80:
        return False
    if raw.startswith(("-", "*", "•")) or re.match(r"^\d+[.)]\s", raw):
        return False
    if raw.lower().startswith("summary:"):
        return False
    if re.match(r"^#{1,6}\s+\S", raw):
        return True
    if re.match(r"^\*\*.+\*\*$", raw) or re.match(r"^__.+__$", raw):
        return True
    label = _strip_heading_markup(raw)
    if not label or label.endswith((".", "!", "?")):
        return False
    if label.endswith(":") or _is_title_case_label(label):
        return True
    # Short first-word-capital labels: "Done when", "What", "Depends on"
    tokens = label.split()
    if not tokens or len(tokens) > 6 or len(label) > 60:
        return False
    return tokens[0][0].isupper()


def _soft_token_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    if a.rstrip("s") == b.rstrip("s") and min(len(a), len(b)) >= 3:
        return True
    if len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return False


# Single-token headings that may expand to multi-word aliases (Done → done when).
# Deliberately excludes "what" so Scope aliases like "what's included" do not steal What→Goal.
_EXPANDABLE_HEADINGS = frozenset({"done", "goal", "goals", "success"})


def _label_matches_aliases(label: str, aliases: tuple[str, ...]) -> bool:
    norm = _normalize_label(label)
    if not norm:
        return False
    tokens = norm.split()
    for alias in aliases:
        a = _normalize_label(alias)
        if not a:
            continue
        if norm == a:
            return True
        a_tokens = [t for t in a.split() if t]
        if not a_tokens:
            continue
        if len(a_tokens) == 1:
            if any(_soft_token_match(token, a_tokens[0]) for token in tokens):
                return True
            continue
        if len(tokens) > 1:
            if all(
                any(_soft_token_match(token, at) for token in tokens) for at in a_tokens
            ):
                return True
            continue
        # Single-token label vs multi-word alias: Done~done when, not What~what's included
        if (
            a_tokens[0] in _EXPANDABLE_HEADINGS
            and _soft_token_match(tokens[0], a_tokens[0])
        ):
            return True
    return False


def _body_has_substance(body: str) -> bool:
    text = re.sub(r"\s+", " ", (body or "")).strip()
    return len(text) >= _SECTION_BODY_MIN_CHARS


def _alias_is_heading_only(alias: str) -> bool:
    a = _normalize_label(alias)
    if not a:
        return True
    if a in _HEADING_ONLY_ALIASES:
        return True
    words = a.split()
    return len(words) == 1 and len(a) <= 4


def _find_heading_section(
    prd_text: str, aliases: tuple[str, ...]
) -> SectionResult | None:
    lines = (prd_text or "").replace("\r\n", "\n").split("\n")
    for idx, line in enumerate(lines):
        raw = line.strip()
        if not raw or not _is_probable_heading(raw):
            continue
        label = _strip_heading_markup(raw)
        if not _label_matches_aliases(label, aliases):
            continue
        body_lines: list[str] = []
        for later in lines[idx + 1 :]:
            nxt = later.strip()
            if nxt and _is_probable_heading(nxt):
                break
            body_lines.append(later)
        body = "\n".join(body_lines).strip()
        if not _body_has_substance(body):
            continue
        evidence = f"{label}: {_normalize(body)[:100]}"
        return SectionResult(name="", present=True, evidence=evidence)
    return None


def _find_phrase_section(
    haystack: str, aliases: tuple[str, ...]
) -> SectionResult | None:
    for alias in aliases:
        if _alias_is_heading_only(alias):
            continue
        needle = alias.lower().strip()
        if not needle:
            continue
        idx = haystack.find(needle)
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(haystack), idx + len(needle) + 60)
            return SectionResult(
                name="", present=True, evidence=haystack[start:end].strip()
            )
    return None


def _find_section(prd_text: str, aliases: tuple[str, ...]) -> SectionResult | None:
    """Prefer synonym-aware headings; fall back to longer phrase matches in body."""
    hit = _find_heading_section(prd_text, aliases)
    if hit:
        return hit
    return _find_phrase_section(_normalize(prd_text), aliases)


def score_sections(
    prd_text: str,
    mandatory_spec: tuple[tuple[str, tuple[str, ...]], ...],
    recommended_spec: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    bug_description_fallback: bool = False,
) -> tuple[tuple[SectionResult, ...], tuple[SectionResult, ...]]:
    """Heuristic presence check for a checklist (synonym + heading aware)."""
    hay = _normalize(prd_text)
    mandatory: list[SectionResult] = []
    for name, aliases in mandatory_spec:
        hit = _find_section(prd_text, aliases)
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
        hit = _find_section(prd_text, aliases)
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
    - trigger=in_progress + any prior KodiQA comment (or legacy Ready) → skip (no double-nag)
    - trigger=to_do + any prior KodiQA comment → skip (scheduled Backlog catch)
    - reporter on skip list (email or display name) → skip all gated types
    """
    trigger_norm = (trigger or "").strip().lower().replace("-", "_")
    if trigger_norm in {"in_progress", "inprogress"} and (prior_comment or prior_ready):
        reason = (
            "In Progress safety net skipped — prior KodiQA comment already exists"
            if prior_comment
            else "In Progress safety net skipped — prior KodiQA gate already Ready"
        )
        return PrdGateResult(
            ticket_key=ticket_key,
            issue_type=issue_type,
            status=status,
            skipped=True,
            skip_reason=reason,
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


# Short plain-English hints shown after bold section names in comments / Slack.
SECTION_HINTS: dict[str, str] = {
    "Goals & objectives": "what are we trying to achieve?",
    "User / persona context": "who is this for?",
    "User stories": "as a ... I want ... so that ...",
    "Functional requirements": "what must the system do?",
    "Acceptance criteria": "how do we know it is done?",
    "Success metrics": "how will we know it worked?",
    "Scope / in-scope": "what is included in this ticket?",
    "Goal": "what are we trying to achieve?",
    "Done when": "what does done look like?",
    "Scope / out of scope": "what is in and what is not",
    "Description": "what is wrong?",
    "Steps to reproduce": "how can someone hit this?",
    "Expected": "what should happen?",
    "Actual": "what happens instead?",
    "Environment": "where did you see it?",
    "Problem / why": "why does this matter?",
    "Outcome / value": "what good looks like when this ships?",
    "Success / done when": "how will we know it worked?",
}


def _ticket_noun(checklist: str) -> str:
    return {
        "bug": "Bug",
        "task": "Task",
        "feature": "Feature",
        "story": "Story",
    }.get(checklist, "ticket")


def _trigger_label(trigger: str) -> str:
    t = (trigger or "").strip().lower().replace("-", "_")
    if t in {"to_do", "todo"}:
        return "To Do"
    if t in {"in_progress", "inprogress"}:
        return "In Progress"
    if not t:
        return "Manual"
    return trigger.strip()


def _missing_section_names(result: PrdGateResult) -> list[str]:
    return [s.name for s in result.mandatory if not s.present]


def _is_in_progress_trigger(trigger: str) -> bool:
    t = (trigger or "").strip().lower().replace("-", "_")
    return t in {"in_progress", "inprogress"}


def _gap_intro_for_creator(missing_count: int, *, trigger: str = "") -> str:
    """To Do = first heads-up. In Progress = last-gate warning."""
    if _is_in_progress_trigger(trigger):
        if missing_count == 1:
            return (
                "You were notified earlier about a quality gap on this ticket, "
                "and it has now been moved to In Progress with that still missing. "
                "Please add the following so the work in progress matches what we need:"
            )
        return (
            "You were notified earlier about quality gaps on this ticket, "
            "and it has now been moved to In Progress without those being added. "
            "Please add the following so the work in progress matches what we need:"
        )
    if missing_count == 1:
        return (
            "Your ticket is missing one thing we need for quality before "
            "the developer starts. Please add:"
        )
    return (
        "Your ticket is missing a few things that we need for quality before "
        "the developer starts. Please add:"
    )


def _soft_check_footer(*, trigger: str = "") -> str:
    if _is_in_progress_trigger(trigger):
        return (
            "This is a soft check only. Ticket status was not changed, "
            "but please fill these in so In Progress work is exactly as required."
        )
    return "This is a soft check only. Ticket status was not changed."


def _gap_line(name: str, *, slack_bold: bool = False) -> str:
    hint = SECTION_HINTS.get(name, "").strip()
    if slack_bold:
        label = f"*{name}*"
    else:
        label = f"**{name}**"
    if hint:
        return f"{label} ({hint})"
    return label


def format_prd_gate_report(result: PrdGateResult) -> str:
    """Human-readable report for CLI (gaps-focused, same voice as comments)."""
    noun = _ticket_noun(result.checklist)
    lines = [
        f"### KodiQA ticket check — `{result.ticket_key}`",
        f"- Type: {result.issue_type}  |  Status: {result.status}",
    ]
    if result.trigger:
        lines.append(f"- Trigger: {_trigger_label(result.trigger)}")
    if result.skipped:
        lines.append(f"- Skipped: {result.skip_reason}")
        return "\n".join(lines) + "\n"

    missing = _missing_section_names(result)
    if not missing:
        lines.append(f"- Looks complete for this {noun}.")
        lines.append("")
        lines.append(_soft_check_footer(trigger=result.trigger))
        return "\n".join(lines) + "\n"

    lines.append("")
    lines.append(_gap_intro_for_creator(len(missing), trigger=result.trigger))
    for name in missing:
        lines.append(f"- {_gap_line(name)}")
    lines.append("")
    lines.append(_soft_check_footer(trigger=result.trigger))
    return "\n".join(lines) + "\n"


def format_prd_gate_slack(
    result: PrdGateResult,
    *,
    reporter: str = "",
    assignee: str = "",
) -> str:
    """Slack DM for the QA lead (not the ticket creator)."""
    noun = _ticket_noun(result.checklist)
    reporter_label = (reporter or "").strip() or "Unknown"
    assignee_label = (assignee or "").strip() or "Unassigned"

    if result.skipped:
        return (
            f"Hey, KodiQA skipped {result.ticket_key} ({result.issue_type}).\n"
            f"Reporter: {reporter_label}\n"
            f"Assignee: {assignee_label}\n"
            f"Reason: {result.skip_reason}"
        )

    missing = _missing_section_names(result)
    if not missing:
        lines = [
            f"Hey, {result.ticket_key} ({noun}) looks complete.",
            f"Reporter: {reporter_label}",
            f"Assignee: {assignee_label}",
        ]
        if result.trigger:
            lines.append(f"Trigger: {_trigger_label(result.trigger)}")
        lines.append("Status was not changed.")
        return "\n".join(lines)

    if _is_in_progress_trigger(result.trigger):
        opener = (
            f"Hey, {result.ticket_key} ({noun}) is In Progress but still has "
            f"quality gaps from the earlier check."
        )
        closer = (
            "Warning comment is on the ticket. Status unchanged. "
            "Please chase the reporter so In Progress work matches requirements."
        )
    else:
        opener = f"Hey, {result.ticket_key} ({noun}) needs a quality pass."
        closer = "Comment is on the ticket. Status unchanged."

    lines = [
        opener,
        f"Reporter: {reporter_label}",
        f"Assignee: {assignee_label}",
    ]
    if result.trigger:
        lines.append(f"Trigger: {_trigger_label(result.trigger)}")
    lines.append("")
    lines.append("Missing:")
    for name in missing:
        lines.append(f"• {_gap_line(name, slack_bold=True)}")
    lines.append("")
    lines.append(closer)
    return "\n".join(lines)


def _adf_text(text: str, *, bold: bool = False) -> dict:
    node: dict = {"type": "text", "text": text}
    if bold:
        node["marks"] = [{"type": "strong"}]
    return node


def _adf_paragraph(*parts: str) -> dict:
    content = [_adf_text(p) for p in parts if p is not None]
    return {"type": "paragraph", "content": content or [_adf_text("")]}


def _adf_paragraph_nodes(nodes: list[dict]) -> dict:
    return {"type": "paragraph", "content": nodes or [_adf_text("")]}


def _adf_heading(text: str, level: int = 3) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [_adf_text(text)],
    }


def _adf_gap_bullet(names: list[str]) -> dict:
    """Bold section name, normal hint in parentheses."""
    items: list[dict] = []
    for name in names:
        hint = SECTION_HINTS.get(name, "").strip()
        parts = [_adf_text(name, bold=True)]
        if hint:
            parts.append(_adf_text(f" ({hint})"))
        items.append(
            {
                "type": "listItem",
                "content": [_adf_paragraph_nodes(parts)],
            }
        )
    return {"type": "bulletList", "content": items}


def _adf_mention(account_id: str, display_name: str) -> dict:
    """Jira @mention inline node (notifies the user)."""
    name = (display_name or "").strip() or "user"
    text = name if name.startswith("@") else f"@{name}"
    return {
        "type": "mention",
        "attrs": {
            "id": account_id,
            "text": text,
            "accessLevel": "",
        },
    }


def _adf_greeting(reporter_account_id: str, reporter_display_name: str) -> dict | None:
    """Hi @Reporter, … or None if we cannot mention."""
    account_id = (reporter_account_id or "").strip()
    if not account_id:
        return None
    return _adf_paragraph_nodes(
        [
            _adf_text("Hi "),
            _adf_mention(account_id, reporter_display_name),
            _adf_text(","),
        ]
    )


def format_prd_gate_jira_adf(
    result: PrdGateResult,
    *,
    reporter_account_id: str = "",
    reporter_display_name: str = "",
) -> dict:
    """Creator-facing Jira comment: gaps only, plain human language, @reporter."""
    nodes: list[dict] = [
        _adf_heading("KodiQA ticket check", 2),
        _adf_paragraph(f"{result.ticket_key} · {result.issue_type}"),
    ]
    greeting = _adf_greeting(reporter_account_id, reporter_display_name)
    if greeting is not None:
        nodes.append(greeting)

    if result.skipped:
        nodes.append(_adf_paragraph(f"Skipped: {result.skip_reason}"))
        nodes.append(_adf_paragraph(_soft_check_footer(trigger=result.trigger)))
        return {"type": "doc", "version": 1, "content": nodes}

    missing = _missing_section_names(result)
    if not missing:
        noun = _ticket_noun(result.checklist)
        nodes.append(
            _adf_paragraph(f"Looks complete for this {noun}. Nice work.")
        )
        nodes.append(_adf_paragraph(_soft_check_footer(trigger=result.trigger)))
        return {"type": "doc", "version": 1, "content": nodes}

    nodes.append(
        _adf_paragraph(
            _gap_intro_for_creator(len(missing), trigger=result.trigger)
        )
    )
    nodes.append(_adf_gap_bullet(missing))
    nodes.append(_adf_paragraph(_soft_check_footer(trigger=result.trigger)))
    return {"type": "doc", "version": 1, "content": nodes}
