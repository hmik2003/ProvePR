from provepr import review as review_mod


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

    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_pull_request(self, full_name, number):
            return {"title": "t", "html_url": "http://x", "number": number}

        def get_pull_request_diff(self, full_name, number):
            return "diff --git a/x b/x\n+hi\n"

    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_issue(self, key):
            return {"key": key, "fields": {"summary": "s", "description": "d"}}

    class FakeGemini:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def generate_text(self, **kwargs):
            calls["gemini"] += 1
            return "Verdict: Insufficient evidence"

    monkeypatch.setattr(review_mod, "load_env", lambda: None)
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
    monkeypatch.setattr(review_mod, "GitHubClient", lambda s: FakeGH())
    monkeypatch.setattr(review_mod, "JiraClient", lambda s: FakeJira())
    monkeypatch.setattr(review_mod, "GeminiClient", lambda s: FakeGemini())
    assert review_mod.run_review(yes=True) == 0
    assert calls["gemini"] == 1


def test_build_user_prompt_truncates():
    huge = "x" * (review_mod.MAX_DIFF_CHARS + 500)
    prompt = review_mod.build_user_prompt(
        pr_title="t",
        pr_url="u",
        ticket_key="SX-1",
        prd="prd",
        diff=huge,
    )
    assert "truncated diff" in prompt
