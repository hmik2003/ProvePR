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
        prior_comment=False,
    )
    assert not result.skipped
    assert result.verdict == "Needs work"


def test_in_progress_dedupe_when_prior_needs_work_comment():
    """SX-4820-style double-nag: To Do already commented → IP must stay quiet."""
    result = evaluate_prd_gate(
        ticket_key="SX-4820",
        issue_type="Task",
        status="In Progress",
        prd_text=THIN_TASK,
        trigger="in_progress",
        prior_ready=False,
        prior_comment=True,
    )
    assert result.skipped
    assert "already exists" in result.skip_reason.lower()


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
    assert "before the developer starts" in text
    assert "soft check" in text.lower()
    assert "status was not changed" in text.lower()


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
    slack = format_prd_gate_slack(result, reporter="Sara", assignee="Unassigned")
    assert "looks complete" in slack.lower()
    assert "Sara" in slack


def test_format_needs_work_human_gaps():
    from provepr.prd_gate import format_prd_gate_jira_adf, format_prd_gate_slack

    result = evaluate_prd_gate(
        ticket_key="SX-4820",
        issue_type="Task",
        status="To Do",
        prd_text=SX4820_STYLE_TASK,
        trigger="to_do",
    )
    assert result.verdict == "Needs work"
    report = format_prd_gate_report(result)
    assert "Scope / out of scope" in report
    assert "before the developer starts" in report
    assert "MISSING" not in report

    slack = format_prd_gate_slack(
        result, reporter="Aqib", assignee="Unassigned"
    )
    assert "Hey, SX-4820" in slack
    assert "Aqib" in slack
    assert "Unassigned" in slack
    assert "Trigger: To Do" in slack
    assert "Your ticket" not in slack
    assert "*Scope / out of scope*" in slack

    adf = format_prd_gate_jira_adf(
        result,
        reporter_account_id="abc-123",
        reporter_display_name="Aqib Khan",
    )
    headings = [
        n["content"][0]["text"]
        for n in adf["content"]
        if n.get("type") == "heading"
    ]
    assert headings == ["KodiQA ticket check"]
    # Greeting tags the reporter
    greet = next(
        n
        for n in adf["content"]
        if n.get("type") == "paragraph"
        and any(p.get("type") == "mention" for p in n.get("content") or [])
    )
    mention = next(p for p in greet["content"] if p.get("type") == "mention")
    assert mention["attrs"]["id"] == "abc-123"
    assert mention["attrs"]["text"] == "@Aqib Khan"
    # Bold gap name in bullet list
    bullet = next(n for n in adf["content"] if n.get("type") == "bulletList")
    first_para = bullet["content"][0]["content"][0]["content"]
    assert first_para[0]["text"] == "Scope / out of scope"
    assert first_para[0].get("marks") == [{"type": "strong"}]
    assert "what is in and what is not" in first_para[1]["text"]


def test_format_in_progress_warning_copy():
    from provepr.prd_gate import format_prd_gate_jira_adf, format_prd_gate_slack

    result = evaluate_prd_gate(
        ticket_key="SX-4820",
        issue_type="Task",
        status="In Progress",
        prd_text=SX4820_STYLE_TASK,
        trigger="in_progress",
    )
    assert result.verdict == "Needs work"
    report = format_prd_gate_report(result)
    assert "notified earlier" in report.lower()
    assert "moved to In Progress" in report
    assert "exactly as required" in report.lower() or "matches what we need" in report

    slack = format_prd_gate_slack(result, reporter="Aqib", assignee="Dev")
    assert "In Progress but still has quality gaps" in slack
    assert "Trigger: In Progress" in slack
    assert "Warning comment" in slack

    adf = format_prd_gate_jira_adf(result)
    intro = next(
        n["content"][0]["text"]
        for n in adf["content"]
        if n.get("type") == "paragraph"
        and n["content"]
        and "notified earlier" in n["content"][0].get("text", "").lower()
    )
    assert "In Progress" in intro


SX4820_STYLE_TASK = """
Summary: Warn when a document-management file is already on the survey

What
When adding files to an existing survey, selecting a document-management file that is already linked looks like a failed upload: the add endpoint treats it as already linked and creates no new row, and the UI still marks the job complete.

Uploading the same set from the computer still works, because that creates a new file.

Done
In add-files mode, document-management files already on this survey stay visible, are not selectable, and show Already on this survey.

If the user submits and the add response marks a file already_linked, show a warning instead of a success state. New files in the same submit are still added, and the warning names the ones that were already linked.

A computer upload of a new copy is unchanged.

Depends on
Existing survey add-files flow (POST /api/v2/site-surveys/{id}/files/) and the document-management picker in the add-files modal. No API change.
"""


def test_sx4820_synonym_headings_recognized():
    """What→Goal, Done→Done when; Scope still missing; Depends on is not Scope."""
    result = evaluate_prd_gate(
        ticket_key="SX-4820",
        issue_type="Task",
        status="To Do",
        prd_text=SX4820_STYLE_TASK,
    )
    by_name = {s.name: s.present for s in result.mandatory}
    assert by_name["Goal"] is True
    assert by_name["Done when"] is True
    assert by_name["Scope / out of scope"] is False
    assert result.verdict == "Needs work"
    assert result.present_count == 2
    assert result.mandatory_total == 3


def test_task_empty_what_heading_does_not_count():
    thin = "What\n\nDone\n\nScope\n\n"
    mandatory, _ = score_task_text(thin)
    assert all(not s.present for s in mandatory)


def test_task_what_in_prose_without_heading_does_not_fake_goal():
    """Ambiguous 'what' in a sentence must not satisfy Goal."""
    prose = (
        "When adding files, check what is already linked before upload. "
        "Also make sure done work is visible somehow."
    )
    mandatory, _ = score_task_text(prose)
    by_name = {s.name: s.present for s in mandatory}
    assert by_name["Goal"] is False
    assert by_name["Done when"] is False


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
        trigger="in_progress",
    )
    report = format_prd_gate_report(feature)
    assert "KodiQA ticket check" in report
    assert "Feature" in report or "SIFU-10" in report
    slack = format_prd_gate_slack(
        feature, reporter="PM", assignee="Dev"
    )
    assert "SIFU-10" in slack
    assert "(Feature)" in slack
    assert "Trigger: In Progress" in slack
    assert "PM" in slack
    adf = format_prd_gate_jira_adf(feature)
    headings = [
        n["content"][0]["text"]
        for n in adf["content"]
        if n.get("type") == "heading"
    ]
    assert headings == ["KodiQA ticket check"]


def test_execute_prd_gate_silent_when_ready(monkeypatch):
    """Ready tickets must not comment or Slack — gaps only."""
    from provepr import prd_gate_cli as cli

    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_issue(self, key):
            return {
                "key": key,
                "fields": {
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                    "summary": "rich",
                    "description": RICH_PRD,
                    "reporter": {"emailAddress": "pm@example.com", "displayName": "PM"},
                },
            }

        def get_subtasks(self, key):
            return []

        def list_comments(self, key):
            return []

        def add_comment(self, key, body):
            raise AssertionError("Ready tickets must not post Jira comments")

    monkeypatch.setattr(cli, "require_jira_settings", lambda: object())
    monkeypatch.setattr(cli, "JiraClient", lambda *_a, **_k: FakeJira())
    monkeypatch.setattr(
        cli,
        "notify_slack",
        lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("Ready tickets must not Slack")
        ),
    )
    monkeypatch.setattr(
        cli, "build_prd_with_subtasks", lambda issue, subtasks: RICH_PRD
    )

    run = cli.execute_prd_gate(ticket="SX-1", comment=True, notify=True)
    assert run.result.verdict == "Ready"
    assert run.jira_comment_url is None


def test_execute_prd_gate_comments_when_needs_work(monkeypatch):
    from provepr import prd_gate_cli as cli

    posted = {}

    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get_issue(self, key):
            return {
                "key": key,
                "fields": {
                    "issuetype": {"name": "Story"},
                    "status": {"name": "To Do"},
                    "summary": "thin",
                    "description": THIN_PRD,
                    "reporter": {"emailAddress": "pm@example.com", "displayName": "PM"},
                },
            }

        def get_subtasks(self, key):
            return []

        def list_comments(self, key):
            return []

        def add_comment(self, key, body):
            posted["key"] = key
            return {"self": "http://jira/comment/1"}

    monkeypatch.setattr(cli, "require_jira_settings", lambda: object())
    monkeypatch.setattr(cli, "JiraClient", lambda *_a, **_k: FakeJira())
    monkeypatch.setattr(
        cli,
        "notify_slack",
        lambda text, kind="pm": type("S", (), {"detail": "Slack OK: DM"})(),
    )
    monkeypatch.setattr(
        cli, "build_prd_with_subtasks", lambda issue, subtasks: THIN_PRD
    )

    run = cli.execute_prd_gate(ticket="SX-2", comment=True, notify=True)
    assert run.result.verdict == "Needs work"
    assert posted["key"] == "SX-2"
    assert run.jira_comment_url == "http://jira/comment/1"
