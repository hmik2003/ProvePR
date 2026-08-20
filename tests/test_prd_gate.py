from provepr.prd_gate import (
    evaluate_prd_gate,
    format_prd_gate_report,
    prior_gate_was_ready,
    score_bug_text,
    score_feature_text,
    score_prd_text,
    score_task_text,
)


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

RICH_BUG = """
## Description
Checkout fails when the cart has a discounted item.

## Steps to reproduce
1. Add a product with a coupon
2. Open checkout
3. Submit payment

## Expected
Order is created and stock is reserved.

## Actual
API returns 500 and no order is written.

## Environment
Chrome 128 / staging / iOS Safari also reproduces.

Screenshot attached for the 500 response.
"""

THIN_BUG = "Checkout broken somehow."

RICH_TASK = """
## Goal
Bump the health endpoint to expose the app version string.

## Done when
- GET /health returns a version field
- Existing status field still works

## Scope / out of scope
In scope: health payload only. Out of scope: changing deploy pipelines.
"""

THIN_TASK = "Do the health thing."

RICH_FEATURE = """
## Problem / why
PMs cannot tell which catalog SKUs are actually sellable, so they over-promise stock.

## Outcome / value
Ops can filter the catalog to in-stock items and trust the list for customer promises.

## Scope / in-scope
List endpoint filter only. No warehouse sync in this feature.

## Acceptance criteria
- GET /api/products?in_stock=true returns only products with stock > 0
- GET /api/products?in_stock=false returns only products with stock = 0
- Omitting in_stock keeps the existing unfiltered list
- Invalid in_stock values return HTTP 400

## Success / done when
GET /api/products?in_stock=true returns only stock > 0; default list unchanged.

## Out of scope
Inventory forecasting.

## Dependencies
Uses existing stock column on products.
"""

THIN_FEATURE = "We should do in-stock someday."


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
    assert result.checklist == "story"


def test_evaluate_needs_work():
    result = evaluate_prd_gate(
        ticket_key="PROV-8",
        issue_type="Story",
        status="To Do",
        prd_text=THIN_PRD,
    )
    assert result.verdict == "Needs work"


def test_evaluate_skips_unsupported_type():
    result = evaluate_prd_gate(
        ticket_key="PROV-1",
        issue_type="Epic",
        status="To Do",
        prd_text=RICH_PRD,
    )
    assert result.skipped
    assert result.verdict == "Skipped"
    assert "Feature" in result.skip_reason
    assert "Spike" not in result.skip_reason


def test_bug_ready_and_thin():
    rich = evaluate_prd_gate(
        ticket_key="PROV-20",
        issue_type="Bug",
        status="To Do",
        prd_text=RICH_BUG,
    )
    assert rich.checklist == "bug"
    assert rich.verdict == "Ready"
    assert all(s.present for s in rich.mandatory)

    thin = evaluate_prd_gate(
        ticket_key="PROV-21",
        issue_type="Bug",
        status="To Do",
        prd_text=THIN_BUG,
    )
    assert thin.verdict == "Needs work"
    assert thin.present_count < thin.mandatory_total


def test_bug_description_length_fallback():
    body = (
        "Users cannot complete checkout after applying a coupon on mobile. "
        "This has been happening since yesterday afternoon on staging."
    )
    # Long prose alone is not enough — still need repro/expected/actual/env
    mandatory, _ = score_bug_text(body)
    assert any(s.name == "Description" and s.present for s in mandatory)
    assert any(s.name == "Steps to reproduce" and not s.present for s in mandatory)


def test_bug_skip_reporter():
    result = evaluate_prd_gate(
        ticket_key="PROV-22",
        issue_type="Bug",
        status="To Do",
        prd_text=THIN_BUG,
        reporter_email="ibrahim.kayani@kodifly.com",
        bug_skip_reporter_emails=("ibrahim.kayani@kodifly.com",),
    )
    assert result.skipped
    assert "skip list" in result.skip_reason.lower()


def test_skip_reporter_applies_to_all_gated_types():
    for issue_type, body in (
        ("Story", THIN_PRD),
        ("Feature", THIN_FEATURE),
        ("Task", THIN_TASK),
        ("Bug", THIN_BUG),
    ):
        result = evaluate_prd_gate(
            ticket_key="KS-1",
            issue_type=issue_type,
            status="To Do",
            prd_text=body,
            reporter_email="ibrahim.kayani@kodifly.com",
            bug_skip_reporter_emails=("ibrahim.kayani@kodifly.com",),
        )
        assert result.skipped, issue_type
        assert "skip list" in result.skip_reason.lower()


def test_skip_reporter_by_display_name():
    result = evaluate_prd_gate(
        ticket_key="KS-2",
        issue_type="Bug",
        status="To Do",
        prd_text=THIN_BUG,
        reporter_display_name="Ibrahim Kayani",
        skip_reporter_names=("Ibrahim Kayani",),
    )
    assert result.skipped
    assert "Ibrahim Kayani" in result.skip_reason


def test_task_ready_and_thin():
    rich = evaluate_prd_gate(
        ticket_key="PROV-30",
        issue_type="Task",
        status="To Do",
        prd_text=RICH_TASK,
    )
    assert rich.checklist == "task"
    assert rich.verdict == "Ready"

    thin = evaluate_prd_gate(
        ticket_key="PROV-31",
        issue_type="Task",
        status="To Do",
        prd_text=THIN_TASK,
    )
    assert thin.verdict == "Needs work"


def test_in_progress_dedupe_when_prior_ready():
    assert prior_gate_was_ready(
        ["KodiQA Bug quality gate\nVerdict: Ready (5/5 mandatory sections)"]
    )
    result = evaluate_prd_gate(
        ticket_key="PROV-40",
        issue_type="Bug",
        status="In Progress",
        prd_text=THIN_BUG,
        trigger="in_progress",
        prior_ready=True,
    )
    assert result.skipped
    assert "already Ready" in result.skip_reason


def test_in_progress_still_runs_when_not_prior_ready():
    result = evaluate_prd_gate(
        ticket_key="PROV-41",
        issue_type="Bug",
        status="In Progress",
        prd_text=THIN_BUG,
        trigger="in_progress",
        prior_ready=False,
    )
    assert not result.skipped
    assert result.verdict == "Needs work"


def test_to_do_dedupe_when_prior_comment_exists():
    from provepr.prd_gate import prior_gate_comment_exists

    assert prior_gate_comment_exists(["KodiQA Feature quality gate\nVerdict: Needs work"])
    result = evaluate_prd_gate(
        ticket_key="KS-537",
        issue_type="Feature",
        status="To Do",
        prd_text="thin",
        trigger="to_do",
        prior_comment=True,
    )
    assert result.skipped
    assert "already exists" in result.skip_reason.lower()


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
    assert "backlog" in text.lower()


def test_format_jira_adf_and_slack():
    from provepr.prd_gate import format_prd_gate_jira_adf, format_prd_gate_slack

    result = evaluate_prd_gate(
        ticket_key="PROV-10",
        issue_type="Story",
        status="To Do",
        prd_text=RICH_PRD,
    )
    adf = format_prd_gate_jira_adf(result)
    assert adf["type"] == "doc"
    assert any(n.get("type") == "heading" for n in adf["content"])
    slack = format_prd_gate_slack(result)
    assert "Ready" in slack
    assert "status" in slack.lower() or "backlog" in slack.lower()


def test_score_task_text_helpers():
    mandatory, recommended = score_task_text(RICH_TASK)
    assert all(s.present for s in mandatory)
    assert recommended == ()


def test_feature_ready_and_thin():
    rich = evaluate_prd_gate(
        ticket_key="SIFU-10",
        issue_type="Feature",
        status="To Do",
        prd_text=RICH_FEATURE,
    )
    assert rich.checklist == "feature"
    assert rich.verdict == "Ready"
    assert all(s.present for s in rich.mandatory)

    thin = evaluate_prd_gate(
        ticket_key="SIFU-11",
        issue_type="New Feature",
        status="To Do",
        prd_text=THIN_FEATURE,
    )
    assert thin.checklist == "feature"
    assert thin.verdict == "Needs work"


def test_feature_needs_acceptance_criteria():
    no_ac = """
## Problem / why
PMs cannot tell which catalog SKUs are actually sellable.

## Outcome / value
Ops can filter the catalog to in-stock items.

## Scope / in-scope
List endpoint filter only.

## Success / done when
in_stock filter is used in catalog sessions.
"""
    result = evaluate_prd_gate(
        ticket_key="SIFU-12",
        issue_type="Feature",
        status="To Do",
        prd_text=no_ac,
    )
    assert result.verdict == "Needs work"
    assert any(s.name == "Acceptance criteria" and not s.present for s in result.mandatory)


def test_spike_skipped_for_now():
    result = evaluate_prd_gate(
        ticket_key="SIFU-20",
        issue_type="Spike",
        status="To Do",
        prd_text="Investigate name sort.",
    )
    assert result.skipped
    assert result.verdict == "Skipped"
    assert "not gated yet" in result.skip_reason.lower()

    research = evaluate_prd_gate(
        ticket_key="SIFU-21",
        issue_type="Research",
        status="To Do",
        prd_text="Look into sorting maybe.",
    )
    assert research.skipped


def test_score_feature_helpers():
    feat_m, feat_r = score_feature_text(RICH_FEATURE)
    assert all(s.present for s in feat_m)
    assert any(s.name == "Out of scope" and s.present for s in feat_r)


def test_format_feature_labels():
    from provepr.prd_gate import format_prd_gate_jira_adf, format_prd_gate_slack

    feature = evaluate_prd_gate(
        ticket_key="SIFU-10",
        issue_type="Feature",
        status="To Do",
        prd_text=THIN_FEATURE,
    )
    assert "Feature quality gate" in format_prd_gate_report(feature)
    slack = format_prd_gate_slack(feature)
    assert "Feature gate" in slack
    adf = format_prd_gate_jira_adf(feature)
    headings = [
        n["content"][0]["text"]
        for n in adf["content"]
        if n.get("type") == "heading"
    ]
    assert any("Feature" in h for h in headings)
