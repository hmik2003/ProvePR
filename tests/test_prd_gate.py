from provepr.prd_gate import evaluate_prd_gate, format_prd_gate_report, score_prd_text


RICH_PRD = """
## Goals & objectives
Shoppers can sort the catalog by price ascending or descending.

## User / persona context
Returning mobile shoppers comparing similar items by price.

## User stories
As a shopper, I want to sort products by price so I can find cheaper options faster.

## Functional requirements
- GET /api/products accepts optional sort=price_asc|price_desc
- Invalid sort values return HTTP 400
- Default (no sort) keeps existing id order

## Acceptance criteria
- sort=price_asc returns products cheapest-first
- sort=price_desc returns products most-expensive-first
- Missing sort returns the same order as today
- Bad sort value returns 400 with a clear message

## Success metrics
At least 15% of catalog sessions use a sort param within 2 weeks (qualitative OK for demo).

## Scope / in-scope
List endpoint sorting only. No UI redesign. No filter changes in this ticket.

## Out of scope
Admin reordering, personalization.

## Edge cases
Equal prices: stable secondary order by id is fine.
"""


THIN_PRD = "Add sorting maybe. Talk to eng."


def test_score_rich_prd_all_mandatory():
    mandatory, recommended = score_prd_text(RICH_PRD)
    assert all(s.present for s in mandatory)
    assert any(s.name == "Out of scope" and s.present for s in recommended)


def test_score_thin_prd_missing():
    mandatory, _ = score_prd_text(THIN_PRD)
    assert sum(1 for s in mandatory if s.present) < len(mandatory)


def test_evaluate_ready():
    result = evaluate_prd_gate(
        ticket_key="PROV-10",
        issue_type="Story",
        status="To Do",
        prd_text=RICH_PRD,
        subtask_count=0,
    )
    assert result.verdict == "Ready"
    assert result.is_ready


def test_evaluate_needs_work():
    result = evaluate_prd_gate(
        ticket_key="PROV-8",
        issue_type="Story",
        status="To Do",
        prd_text=THIN_PRD,
    )
    assert result.verdict == "Needs work"


def test_evaluate_skips_non_story():
    result = evaluate_prd_gate(
        ticket_key="PROV-1",
        issue_type="Bug",
        status="To Do",
        prd_text=RICH_PRD,
    )
    assert result.skipped
    assert result.verdict == "Skipped"


def test_format_report_mentions_soft_gate():
    result = evaluate_prd_gate(
        ticket_key="PROV-10",
        issue_type="Story",
        status="To Do",
        prd_text=THIN_PRD,
    )
    text = format_prd_gate_report(result)
    assert "Needs work" in text
    assert "soft gate" in text.lower() or "Soft gate" in text
