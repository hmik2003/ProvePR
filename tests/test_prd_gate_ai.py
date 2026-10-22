from provepr.prd_gate import evaluate_prd_gate
from provepr.prd_gate_ai import (
    maybe_refine_prd_gate_result,
    needs_ai_disambiguation,
    refine_mandatory_with_ai,
)
from tests.test_prd_gate import RICH_TASK, THIN_TASK

# Goal + Done via synonyms; Scope uses an unknown label (not in alias list).
GAP_SCOPE_TASK = """
What
When adding files to an existing survey, selecting a document-management file that is
already linked looks like a failed upload because the add endpoint returns already_linked
and the UI still marks the job complete without a clear warning for the operator.

Done
In add-files mode, document-management files already on this survey stay visible, are not
selectable, and show Already on this survey. Warn on submit when already_linked is returned.

Coverage limits
Only the add-files modal picker UX and warning copy. Do not change the API unique
constraint or the computer-upload path that creates a new file copy.
"""


def test_needs_ai_false_when_ready():
    result = evaluate_prd_gate(
        ticket_key="T-1",
        issue_type="Task",
        status="To Do",
        prd_text=RICH_TASK,
    )
    assert result.verdict == "Ready"
    assert needs_ai_disambiguation(result.mandatory, RICH_TASK) is False


def test_needs_ai_false_when_thin():
    result = evaluate_prd_gate(
        ticket_key="T-2",
        issue_type="Task",
        status="To Do",
        prd_text=THIN_TASK,
    )
    assert result.verdict == "Needs work"
    assert needs_ai_disambiguation(result.mandatory, THIN_TASK) is False


def test_needs_ai_true_when_substantial_gaps():
    result = evaluate_prd_gate(
        ticket_key="T-3",
        issue_type="Task",
        status="To Do",
        prd_text=GAP_SCOPE_TASK,
    )
    assert result.verdict == "Needs work"
    assert any(s.name == "Scope / out of scope" and not s.present for s in result.mandatory)
    assert needs_ai_disambiguation(result.mandatory, GAP_SCOPE_TASK) is True


def test_maybe_refine_skips_model_on_ready():
    calls = {"n": 0}

    def boom(**_kwargs):
        calls["n"] += 1
        raise AssertionError("AI must not run on Ready")

    result = evaluate_prd_gate(
        ticket_key="T-4",
        issue_type="Task",
        status="To Do",
        prd_text=RICH_TASK,
    )
    out = maybe_refine_prd_gate_result(result, RICH_TASK, generate_text=boom)
    assert out.verdict == "Ready"
    assert calls["n"] == 0


def test_maybe_refine_skips_model_on_thin():
    calls = {"n": 0}

    def boom(**_kwargs):
        calls["n"] += 1
        raise AssertionError("AI must not run on thin stubs")

    result = evaluate_prd_gate(
        ticket_key="T-5",
        issue_type="Task",
        status="To Do",
        prd_text=THIN_TASK,
    )
    out = maybe_refine_prd_gate_result(result, THIN_TASK, generate_text=boom)
    assert out.verdict == "Needs work"
    assert calls["n"] == 0


def test_maybe_refine_rescues_missing_via_ai():
    result = evaluate_prd_gate(
        ticket_key="T-6",
        issue_type="Task",
        status="To Do",
        prd_text=GAP_SCOPE_TASK,
    )
    assert result.verdict == "Needs work"

    def fake_generate(**_kwargs):
        return '{"present":["Scope / out of scope"]}'

    out = maybe_refine_prd_gate_result(
        result, GAP_SCOPE_TASK, generate_text=fake_generate, enabled=True
    )
    assert out.verdict == "Ready"
    assert all(s.present for s in out.mandatory)


def test_refine_ignores_unknown_section_names():
    result = evaluate_prd_gate(
        ticket_key="T-7",
        issue_type="Task",
        status="To Do",
        prd_text=GAP_SCOPE_TASK,
    )
    assert result.verdict == "Needs work"

    def fake_generate(**_kwargs):
        return '{"present":["Unicorn section", "Scope / out of scope"]}'

    mandatory, called = refine_mandatory_with_ai(
        checklist="task",
        mandatory=result.mandatory,
        prd_text=GAP_SCOPE_TASK,
        generate_text=fake_generate,
    )
    assert called is True
    by_name = {s.name: s.present for s in mandatory}
    assert by_name["Scope / out of scope"] is True


def test_maybe_refine_disabled():
    calls = {"n": 0}

    def fake_generate(**_kwargs):
        calls["n"] += 1
        return '{"present":["Scope / out of scope"]}'

    result = evaluate_prd_gate(
        ticket_key="T-8",
        issue_type="Task",
        status="To Do",
        prd_text=GAP_SCOPE_TASK,
    )
    out = maybe_refine_prd_gate_result(
        result, GAP_SCOPE_TASK, generate_text=fake_generate, enabled=False
    )
    assert calls["n"] == 0
    assert out.verdict == "Needs work"


def test_ai_failure_keeps_heuristic_result():
    result = evaluate_prd_gate(
        ticket_key="T-9",
        issue_type="Task",
        status="To Do",
        prd_text=GAP_SCOPE_TASK,
    )
    assert result.verdict == "Needs work"

    def boom(**_kwargs):
        raise RuntimeError("quota")

    out = maybe_refine_prd_gate_result(
        result, GAP_SCOPE_TASK, generate_text=boom, enabled=True
    )
    assert out.verdict == "Needs work"
    assert out.present_count == result.present_count
