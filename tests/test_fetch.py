from provepr import fetch as fetch_mod


def test_run_fetch_ok(monkeypatch):
    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_pull_request(self, full_name, number):
            return {
                "number": number,
                "title": "DEMO-1: sample",
                "html_url": f"https://github.com/{full_name}/pull/{number}",
            }

        def get_pull_request_diff(self, full_name, number):
            return "diff --git a/x b/x\n+hello\n"

    class FakeJira:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_issue(self, key):
            return {
                "key": key,
                "fields": {
                    "summary": "Sample requirement",
                    "description": "Do the thing.",
                },
            }

    monkeypatch.setattr(fetch_mod, "require_github_settings", lambda: object())
    monkeypatch.setattr(fetch_mod, "require_jira_settings", lambda: object())
    monkeypatch.setattr(fetch_mod, "GitHubClient", lambda settings: FakeGH())
    monkeypatch.setattr(fetch_mod, "JiraClient", lambda settings: FakeJira())

    assert (
        fetch_mod.run_fetch(repo="hmik2003/ProvePR", pr=1, ticket="DEMO-1") == 0
    )


def test_run_fetch_missing_targets(monkeypatch):
    monkeypatch.setattr(fetch_mod, "load_env", lambda: None)
    monkeypatch.delenv("GITHUB_TEST_REPO", raising=False)
    monkeypatch.delenv("GITHUB_TEST_PR_NUMBER", raising=False)
    monkeypatch.delenv("JIRA_TEST_TICKET", raising=False)
    assert fetch_mod.run_fetch() == 1
