from provepr.development_link import (
    check_pr_linked_in_development,
    format_development_advisory,
)
from provepr.jira_key import extract_jira_keys, primary_jira_key_from_title
from provepr.jira_text import build_prd_with_subtasks
from provepr import review as review_mod


def _fake_gh(title: str = "SX-2869: feature"):
    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_pull_request(self, full_name, number):
            return {
                "title": title,
                "html_url": f"https://github.com/{full_name}/pull/{number}",
                "number": number,
            }

        def get_pull_request_diff(self, full_name, number):
            return "diff --git a/x b/x\n+hi\n"

        def create_issue_comment(self, full_name, number, body):
            self.last_body = body
            return {"html_url": "http://comment"}

    return FakeGH()


def _fake_jira(*, linked: bool = False, unavailable: bool = False):
    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_issue(self, key, fields=None):
            return {
                "id": "10001",
                "key": key,
                "fields": {"summary": "s", "description": "d"},
            }

        def get_subtasks(self, key):
            return []

        def get_development_pull_requests(self, issue):
            if unavailable:
                return [], "No permission to read Development panel"
            if linked:
                return [
                    {
                        "id": "1",
                        "url": "https://github.com/hmik2003/ProvePR/pull/1",
                        "name": "Pull request #1",
                    }
                ], None
            return [], None

    return FakeJira()


def test_run_review_dry_run_no_gemini(monkeypatch):
    calls = {"gemini": 0}

    class BoomClient:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def generate_text(self, **kwargs):
            calls["gemini"] += 1
            raise AssertionError("should not call Gemini on dry-run")

    monkeypatch.setattr(review_mod, "load_env", lambda: None)
    monkeypatch.setattr(review_mod, "hermes_available", lambda: False)
    monkeypatch.setattr(
        review_mod,
        "resolve_targets",
        lambda **kw: ("hmik2003/ProvePR", 1, "SX-2869"),
    )
    monkeypatch.setattr(
        review_mod,
        "require_gemini_settings",
        lambda: type("S", (), {"model": "gemini-2.0-flash", "api_key": "x"})(),
    )
    monkeypatch.setattr(review_mod, "GeminiClient", lambda settings: BoomClient())
    assert review_mod.run_review(yes=False) == 0
    assert calls["gemini"] == 0


def test_run_review_yes_calls_gemini_once(monkeypatch):
    calls = {"gemini": 0}

    class FakeGemini:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def generate_text(self, **kwargs):
            calls["gemini"] += 1
            return "Verdict: Insufficient evidence"

    monkeypatch.setattr(review_mod, "load_env", lambda: None)
    monkeypatch.setattr(review_mod, "hermes_available", lambda: False)
    monkeypatch.setattr(
        review_mod,
        "resolve_targets",
        lambda **kw: ("hmik2003/ProvePR", 1, "SX-2869"),
    )
    monkeypatch.setattr(
        review_mod,
        "require_gemini_settings",
        lambda: type("S", (), {"model": "gemini-2.0-flash", "api_key": "x"})(),
    )
    monkeypatch.setattr(review_mod, "require_github_settings", lambda: object())
    monkeypatch.setattr(review_mod, "require_jira_settings", lambda: object())
    monkeypatch.setattr(review_mod, "GitHubClient", lambda s: _fake_gh())
    monkeypatch.setattr(review_mod, "JiraClient", lambda s: _fake_jira())
    monkeypatch.setattr(review_mod, "GeminiClient", lambda s: FakeGemini())
    assert review_mod.run_review(yes=True) == 0
    assert calls["gemini"] == 1


def test_run_review_yes_uses_hermes_when_available(monkeypatch):
    calls = {"hermes": 0}

    monkeypatch.setattr(review_mod, "load_env", lambda: None)
    monkeypatch.setattr(review_mod, "hermes_available", lambda: True)
    monkeypatch.setattr(
        review_mod,
        "resolve_targets",
        lambda **kw: ("hmik2003/provepr-demo-shop", 5, "PROV-5"),
    )
    monkeypatch.setattr(
        review_mod,
        "require_gemini_settings",
        lambda: type("S", (), {"model": "gemini-flash-lite-latest", "api_key": "x"})(),
    )
    monkeypatch.setattr(review_mod, "require_github_settings", lambda: object())
    monkeypatch.setattr(review_mod, "require_jira_settings", lambda: object())
    monkeypatch.setattr(
        review_mod, "GitHubClient", lambda s: _fake_gh("PROV-5: empty ticket")
    )
    monkeypatch.setattr(review_mod, "JiraClient", lambda s: _fake_jira())

    def fake_hermes(**kwargs):
        calls["hermes"] += 1
        assert kwargs["repo"] == "hmik2003/provepr-demo-shop"
        assert kwargs["pr"] == 5
        assert kwargs["ticket_key"] == "PROV-5"
        return "1. **PRD quality assessment:** Vague\n2. **Verdict:** Insufficient evidence"

    monkeypatch.setattr(review_mod, "run_hermes_review", fake_hermes)
    assert review_mod.run_review(yes=True) == 0
    assert calls["hermes"] == 1


def test_run_review_rejects_multiple_title_keys(monkeypatch):
    monkeypatch.setattr(review_mod, "load_env", lambda: None)
    monkeypatch.setattr(review_mod, "hermes_available", lambda: False)
    monkeypatch.setattr(
        review_mod,
        "resolve_targets",
        lambda **kw: ("hmik2003/ProvePR", 1, "PROV-1"),
    )
    monkeypatch.setattr(
        review_mod,
        "require_gemini_settings",
        lambda: type("S", (), {"model": "gemini-2.0-flash", "api_key": "x"})(),
    )
    monkeypatch.setattr(review_mod, "require_github_settings", lambda: object())
    monkeypatch.setattr(review_mod, "require_jira_settings", lambda: object())
    monkeypatch.setattr(
        review_mod,
        "GitHubClient",
        lambda s: _fake_gh("PROV-1 PROV-2: two tickets"),
    )
    assert review_mod.run_review(yes=True) == 1


def test_format_pr_comment_includes_development_advisory():
    from provepr.development_link import DevelopmentLinkCheck

    body = review_mod.format_pr_comment(
        ticket_key="PROV-6",
        model="Hermes + gemini-flash-lite-latest",
        review_text="0. **TL;DR**\n- **Verdict:** Requirements largely met",
        development=DevelopmentLinkCheck(
            status="not_linked",
            message="Please link this PR.",
        ),
    )
    assert "PROV-6" in body
    assert "Development panel" in body
    assert "Not linked" in body
    assert "Non-blocking" in body


def test_format_pr_comment_mentions_tldr_guidance():
    body = review_mod.format_pr_comment(
        ticket_key="PROV-6",
        model="Hermes + gemini-flash-lite-latest",
        review_text="0. **TL;DR**\n- **Verdict:** Requirements largely met",
    )
    assert "PROV-6" in body
    assert "TL;DR" in body
    assert "Must-fix" in body or "Blocker/Major" in body


def test_build_user_prompt_includes_tldr_and_truncates():
    huge = "x" * (review_mod.MAX_DIFF_CHARS + 500)
    prompt = review_mod.build_user_prompt(
        pr_title="t",
        pr_url="u",
        ticket_key="SX-1",
        prd="prd",
        diff=huge,
    )
    assert "truncated diff" in prompt
    assert "TL;DR" in prompt
    assert "Must-fix" in prompt


def test_run_review_post_requires_yes(monkeypatch):
    monkeypatch.setattr(review_mod, "load_env", lambda: None)
    assert review_mod.run_review(yes=False, post=True) == 1


def test_run_review_yes_post_github_and_slack_stub(monkeypatch):
    calls = {"gemini": 0, "comment": 0}

    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_pull_request(self, full_name, number):
            return {
                "title": "SX-2869: feature",
                "html_url": f"https://github.com/{full_name}/pull/{number}",
                "number": number,
            }

        def get_pull_request_diff(self, full_name, number):
            return "diff --git a/x b/x\n+hi\n"

        def create_issue_comment(self, full_name, number, body):
            calls["comment"] += 1
            assert "ProvePR review" in body
            assert "Development panel" in body
            assert "Hermes" in body or "single-shot" in body or "gemini" in body.lower()
            return {"html_url": "http://comment"}

    class FakeGemini:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def generate_text(self, **kwargs):
            calls["gemini"] += 1
            return "Verdict: Insufficient evidence"

    monkeypatch.setattr(review_mod, "load_env", lambda: None)
    monkeypatch.setattr(review_mod, "hermes_available", lambda: False)
    monkeypatch.setattr(
        review_mod,
        "resolve_targets",
        lambda **kw: ("hmik2003/ProvePR", 1, "SX-2869"),
    )
    monkeypatch.setattr(
        review_mod,
        "require_gemini_settings",
        lambda: type("S", (), {"model": "gemini-flash-lite-latest", "api_key": "x"})(),
    )
    monkeypatch.setattr(review_mod, "require_github_settings", lambda: object())
    monkeypatch.setattr(review_mod, "require_jira_settings", lambda: object())
    monkeypatch.setattr(review_mod, "GitHubClient", lambda s: FakeGH())
    monkeypatch.setattr(review_mod, "JiraClient", lambda s: _fake_jira())
    monkeypatch.setattr(review_mod, "GeminiClient", lambda s: FakeGemini())
    monkeypatch.setattr(
        review_mod,
        "notify_slack",
        lambda text: type("R", (), {"posted": False, "detail": "Slack stub: skipped"})(),
    )
    assert review_mod.run_review(yes=True, post=True) == 0
    assert calls["gemini"] == 1
    assert calls["comment"] == 1


def test_check_pr_linked_matches_number():
    result = check_pr_linked_in_development(
        pr_number=12,
        pr_html_url="https://github.com/o/r/pull/12",
        pull_requests=[{"id": "12", "url": "https://github.com/o/r/pull/12"}],
    )
    assert result.status == "linked"


def test_check_pr_not_linked():
    result = check_pr_linked_in_development(
        pr_number=12,
        pr_html_url="https://github.com/o/r/pull/12",
        pull_requests=[{"id": "99", "url": "https://github.com/o/r/pull/99"}],
    )
    assert result.status == "not_linked"
    assert "does **not** block" in result.message or "not** found" in result.message


def test_format_development_advisory_not_linked():
    result = check_pr_linked_in_development(
        pr_number=1, pr_html_url=None, pull_requests=[]
    )
    text = format_development_advisory(result)
    assert "Not linked" in text
    assert "Non-blocking" in text


def test_primary_jira_key_from_title_single():
    primary, keys = primary_jira_key_from_title("PROV-9: stock")
    assert primary == "PROV-9"
    assert keys == ["PROV-9"]


def test_primary_jira_key_from_title_multiple():
    primary, keys = primary_jira_key_from_title("PROV-1 and PROV-2")
    assert primary is None
    assert keys == ["PROV-1", "PROV-2"]


def test_extract_jira_keys_order():
    assert extract_jira_keys("ZZZ-1 then AAA-2") == ["ZZZ-1", "AAA-2"]


def test_build_prd_with_subtasks():
    parent = {
        "key": "PROV-9",
        "fields": {"summary": "Parent", "description": "Parent body"},
    }
    children = [
        {
            "key": "PROV-10",
            "fields": {
                "summary": "Child",
                "description": "Child AC",
                "status": {"name": "To Do"},
            },
        }
    ]
    text = build_prd_with_subtasks(parent, children)
    assert "Parent ticket PROV-9" in text
    assert "Subtask PROV-10" in text
    assert "Child AC" in text
