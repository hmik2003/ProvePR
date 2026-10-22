"""Cheap Gemini assist for PRD gate — only when heuristics are ambiguous."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable

from provepr.config import GeminiSettings, gemini_key_present, load_env, require_gemini_settings
from provepr.gemini_client import GeminiClient
from provepr.prd_gate import PrdGateResult, SectionResult, _normalize

# Substantial body but checklist gaps → possible false negatives from unknown labels.
_AI_BODY_MIN_CHARS = 120
_AI_TEXT_MAX_CHARS = 6000
_AI_MAX_OUTPUT_TOKENS = 320

_SYSTEM = (
    "You check Jira ticket quality checklists. "
    "Given MISSING section names and the ticket text, decide which missing sections "
    "are already satisfied under any heading, synonym, or clear prose. "
    "Be conservative: only mark a section present when the text clearly covers it. "
    "Reply with JSON only, no markdown: "
    '{"present":["Exact Section Name",...]}'
)


GenerateText = Callable[..., str]


def prd_gate_ai_enabled() -> bool:
    load_env()
    raw = (os.getenv("PRD_GATE_AI") or "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def prd_gate_gemini_settings() -> GeminiSettings | None:
    """Settings for the gate assist call (optional cheaper model override)."""
    load_env()
    if not gemini_key_present():
        return None
    base = require_gemini_settings()
    override = (os.getenv("PRD_GATE_GEMINI_MODEL") or "").strip()
    if override:
        return GeminiSettings(api_key=base.api_key, model=override)
    return base


def needs_ai_disambiguation(
    mandatory: tuple[SectionResult, ...],
    prd_text: str,
) -> bool:
    """
    True only when heuristics left gaps but the ticket has enough text that
    unknown headings/synonyms might still satisfy those gaps.
    Clear Ready and thin stubs stay free (no model call).
    """
    missing = [s for s in mandatory if not s.present]
    if not missing:
        return False
    if len(_normalize(prd_text)) < _AI_BODY_MIN_CHARS:
        return False
    return True


def _truncate(text: str, limit: int = _AI_TEXT_MAX_CHARS) -> str:
    body = (text or "").strip()
    if len(body) <= limit:
        return body
    return body[: limit - 20].rstrip() + "\n…[truncated]"


def _parse_present_names(raw: str, allowed: set[str]) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Best-effort: find a JSON object in the response
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    if not isinstance(data, dict):
        return []
    present = data.get("present")
    if not isinstance(present, list):
        return []
    found: list[str] = []
    allowed_lower = {name.lower(): name for name in allowed}
    for item in present:
        name = str(item or "").strip()
        if not name:
            continue
        if name in allowed:
            found.append(name)
        elif name.lower() in allowed_lower:
            found.append(allowed_lower[name.lower()])
    return found


def build_ai_user_prompt(
    *,
    checklist: str,
    missing_names: list[str],
    present_names: list[str],
    prd_text: str,
) -> str:
    lines = [
        f"Checklist type: {checklist}",
        "",
        "Missing sections (only these may be rescued):",
        *[f"- {name}" for name in missing_names],
        "",
        "Already detected present (do not re-list):",
    ]
    if present_names:
        lines.extend(f"- {name}" for name in present_names)
    else:
        lines.append("- (none)")
    lines.extend(["", "Ticket text:", _truncate(prd_text)])
    return "\n".join(lines)


def refine_mandatory_with_ai(
    *,
    checklist: str,
    mandatory: tuple[SectionResult, ...],
    prd_text: str,
    generate_text: GenerateText | None = None,
    settings: GeminiSettings | None = None,
) -> tuple[tuple[SectionResult, ...], bool]:
    """
    Ask Gemini which heuristic-MISSING sections are actually covered.

    Returns (updated mandatory sections, whether a model call was made).
    On any failure, returns the original mandatory unchanged.
    """
    missing = [s for s in mandatory if not s.present]
    if not missing:
        return mandatory, False

    missing_names = [s.name for s in missing]
    present_names = [s.name for s in mandatory if s.present]
    user = build_ai_user_prompt(
        checklist=checklist,
        missing_names=missing_names,
        present_names=present_names,
        prd_text=prd_text,
    )

    try:
        if generate_text is not None:
            raw = generate_text(
                system=_SYSTEM,
                user=user,
                max_output_tokens=_AI_MAX_OUTPUT_TOKENS,
                temperature=0.1,
            )
        else:
            cfg = settings or prd_gate_gemini_settings()
            if cfg is None:
                return mandatory, False
            with GeminiClient(cfg) as client:
                raw = client.generate_text(
                    system=_SYSTEM,
                    user=user,
                    max_output_tokens=_AI_MAX_OUTPUT_TOKENS,
                    temperature=0.1,
                )
    except Exception:  # noqa: BLE001 — soft gate must never fail closed on AI
        return mandatory, False

    rescued = set(_parse_present_names(raw, set(missing_names)))
    if not rescued:
        return mandatory, True

    updated: list[SectionResult] = []
    for section in mandatory:
        if section.name in rescued and not section.present:
            updated.append(
                SectionResult(
                    name=section.name,
                    present=True,
                    evidence="(AI: covered under alternate wording)",
                )
            )
        else:
            updated.append(section)
    return tuple(updated), True


def maybe_refine_prd_gate_result(
    result: PrdGateResult,
    prd_text: str,
    *,
    generate_text: GenerateText | None = None,
    settings: GeminiSettings | None = None,
    enabled: bool | None = None,
) -> PrdGateResult:
    """
    Cost gate: only call the model when Needs work + substantial body.
    Ready / Skipped / thin stubs / disabled / no API key → unchanged.
    """
    if result.skipped or result.verdict != "Needs work":
        return result
    if enabled is None:
        enabled = prd_gate_ai_enabled()
    if not enabled:
        return result
    if not needs_ai_disambiguation(result.mandatory, prd_text):
        return result
    if generate_text is None and prd_gate_gemini_settings() is None and settings is None:
        return result

    mandatory, _called = refine_mandatory_with_ai(
        checklist=result.checklist,
        mandatory=result.mandatory,
        prd_text=prd_text,
        generate_text=generate_text,
        settings=settings,
    )
    if mandatory == result.mandatory:
        return result

    present = sum(1 for s in mandatory if s.present)
    total = len(mandatory)
    verdict = "Ready" if present == total else "Needs work"
    return PrdGateResult(
        ticket_key=result.ticket_key,
        issue_type=result.issue_type,
        status=result.status,
        skipped=False,
        skip_reason="",
        verdict=verdict,
        mandatory=mandatory,
        recommended=result.recommended,
        present_count=present,
        mandatory_total=total,
        subtask_count=result.subtask_count,
        checklist=result.checklist,
        trigger=result.trigger,
    )
