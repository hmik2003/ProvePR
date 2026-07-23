"""ProvePR Hermes plugin — registers Jira/GitHub review tools."""

from __future__ import annotations


def register(ctx) -> None:
    # Import handlers from the ProvePR package (PYTHONPATH must include src/).
    from provepr.hermes_tools import (
        SCHEMA_GET_JIRA_PRD,
        SCHEMA_GET_PULL_REQUEST,
        SCHEMA_GET_PULL_REQUEST_DIFF,
        get_jira_prd,
        get_pull_request,
        get_pull_request_diff,
    )

    ctx.register_tool(
        name="get_jira_prd",
        toolset="provepr",
        schema=SCHEMA_GET_JIRA_PRD,
        handler=get_jira_prd,
        description="Fetch Jira PRD text",
    )
    ctx.register_tool(
        name="get_pull_request",
        toolset="provepr",
        schema=SCHEMA_GET_PULL_REQUEST,
        handler=get_pull_request,
        description="Fetch GitHub PR metadata",
    )
    ctx.register_tool(
        name="get_pull_request_diff",
        toolset="provepr",
        schema=SCHEMA_GET_PULL_REQUEST_DIFF,
        handler=get_pull_request_diff,
        description="Fetch GitHub PR unified diff",
    )
