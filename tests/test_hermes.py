import json
import sys
import types

from provepr import hermes_review as hermes_mod
from provepr import hermes_tools as tools


def test_get_jira_prd_success(monkeypatch):
    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_issue(self, key):
            return {
                "key": key,
                "fields": {"summary": "Coupons", "description": "Add coupons maybe."},
            }

    monkeypatch.setattr(tools, "require_jira_settings", lambda: object())
    monkeypatch.setattr(tools, "JiraClient", lambda s: FakeJira())
    monkeypatch.setattr(
        tools,
        "issue_prd_text",
        lambda issue: "Summary: Coupons\n\nAdd coupons maybe.",
    )
    raw = tools.get_jira_prd({"ticket_key": "PROV-5"})
    data = json.loads(raw)
    assert data["ticket_key"] == "PROV-5"
    assert "coupons" in data["prd"].lower()


def test_get_jira_prd_requires_key():
    data = json.loads(tools.get_jira_prd({}))
    assert "error" in data


def test_get_pull_request_and_diff(monkeypatch):
    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_pull_request(self, full_name, number):
            return {
                "number": number,
                "title": "PROV-5: coupons",
                "html_url": "http://example/pr",
                "body": "x",
                "head": {"ref": "feature/PROV-5"},
                "base": {"ref": "staging"},
            }

        def get_pull_request_diff(self, full_name, number):
            return "diff --git a/app/coupons.py b/app/coupons.py\n+ok\n"

    monkeypatch.setattr(tools, "require_github_settings", lambda: object())
    monkeypatch.setattr(tools, "GitHubClient", lambda s: FakeGH())

    meta = json.loads(
        tools.get_pull_request({"repo": "hmik2003/provepr-demo-shop", "pr": 5})
    )
    assert meta["title"] == "PROV-5: coupons"
    assert meta["base_ref"] == "staging"

    diff = json.loads(
        tools.get_pull_request_diff({"repo": "hmik2003/provepr-demo-shop", "pr": 5})
    )
    assert "coupons.py" in diff["diff"]


def test_build_hermes_user_message_includes_targets():
    msg = hermes_mod.build_hermes_user_message(
        repo="hmik2003/provepr-demo-shop",
        pr=5,
        ticket_key="PROV-5",
    )
    assert "PROV-5" in msg
    assert "get_jira_prd" in msg
    assert "get_pull_request_diff" in msg


def test_run_hermes_review_uses_agent(monkeypatch):
    class FakeAgent:
        def __init__(self, **kwargs):
            assert kwargs["provider"] == "gemini"
            assert kwargs["enabled_toolsets"] == ["provepr"]
            assert kwargs["max_iterations"] == hermes_mod.MAX_HERMES_ITERATIONS

        def run_conversation(self, user_message=None, **kwargs):
            assert "PROV-5" in (user_message or "")
            return {"final_response": "Hermes review body"}

    run_agent = types.ModuleType("run_agent")
    run_agent.AIAgent = FakeAgent
    monkeypatch.setitem(sys.modules, "run_agent", run_agent)

    hermes_cli = types.ModuleType("hermes_cli")
    plugins = types.ModuleType("hermes_cli.plugins")
    plugins.discover_plugins = lambda: None
    hermes_cli.plugins = plugins
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.plugins", plugins)

    monkeypatch.setattr(hermes_mod, "register_provepr_tools", lambda force=False: None)

    text = hermes_mod.run_hermes_review(
        repo="hmik2003/provepr-demo-shop",
        pr=5,
        ticket_key="PROV-5",
        gemini=type("S", (), {"model": "gemini-flash-lite-latest", "api_key": "x"})(),
        system_prompt="sys",
    )
    assert text == "Hermes review body"
