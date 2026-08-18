"""Local demo of Story/Bug/Task/Feature soft quality gates (offline)."""

from __future__ import annotations

import sys

from provepr.prd_gate import (
    evaluate_prd_gate,
    format_prd_gate_report,
    format_prd_gate_slack,
)


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
Chrome 128 / staging
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
PMs cannot tell which catalog SKUs are actually sellable.

## Outcome / value
Ops can filter the catalog to in-stock items.

## Scope / in-scope
List endpoint filter only.

## Acceptance criteria
- in_stock=true returns only stock > 0
- omitting in_stock keeps the existing list

## Success / done when
GET /api/products?in_stock=true returns only stock > 0.
"""

THIN_FEATURE = "We should do in-stock someday."


def show(label: str, **kwargs) -> None:
    result = evaluate_prd_gate(ticket_key="DEMO-1", **kwargs)
    print()
    print("=" * 64)
    print(label)
    print("=" * 64)
    print(format_prd_gate_report(result), end="")
    print("--- Slack preview ---")
    print(format_prd_gate_slack(result))


def main() -> int:
    print("LOCAL DEMO — KodiQA soft gates (no network)")
    show(
        "1) Bug READY (full QA template)",
        issue_type="Bug",
        status="To Do",
        prd_text=RICH_BUG,
        trigger="to_do",
    )
    show(
        "2) Bug NEEDS WORK (title-only style body)",
        issue_type="Bug",
        status="To Do",
        prd_text=THIN_BUG,
        trigger="to_do",
    )
    show(
        "3) Task READY (light checklist)",
        issue_type="Task",
        status="To Do",
        prd_text=RICH_TASK,
        trigger="to_do",
    )
    show(
        "4) Task NEEDS WORK",
        issue_type="Task",
        status="To Do",
        prd_text=THIN_TASK,
        trigger="to_do",
    )
    show(
        "5) In Progress safety net - prior Ready => skip (no double-nag)",
        issue_type="Bug",
        status="In Progress",
        prd_text=THIN_BUG,
        trigger="in_progress",
        prior_ready=True,
    )
    show(
        "6) In Progress safety net - never Ready => still Needs work",
        issue_type="Bug",
        status="In Progress",
        prd_text=THIN_BUG,
        trigger="in_progress",
        prior_ready=False,
    )
    show(
        "7) Bug reporter on skip list => skipped",
        issue_type="Bug",
        status="To Do",
        prd_text=THIN_BUG,
        reporter_email="ibrahim.kayani@kodifly.com",
        bug_skip_reporter_emails=("ibrahim.kayani@kodifly.com",),
        trigger="to_do",
    )
    show(
        "8) Feature READY",
        issue_type="Feature",
        status="To Do",
        prd_text=RICH_FEATURE,
        trigger="to_do",
    )
    show(
        "9) Feature NEEDS WORK",
        issue_type="Feature",
        status="To Do",
        prd_text=THIN_FEATURE,
        trigger="to_do",
    )
    show(
        "10) Spike SKIPPED (not gated yet)",
        issue_type="Spike",
        status="To Do",
        prd_text="Investigate name sort.",
        trigger="to_do",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
