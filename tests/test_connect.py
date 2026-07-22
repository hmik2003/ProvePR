from provepr import connect as connect_mod


def test_run_connect_github_ok(monkeypatch):
    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def get_authenticated_user(self):
            return {"login": "hmik2003"}

        def get_repo(self, full_name):
            return {"full_name": full_name, "private": False}

    monkeypatch.setattr(connect_mod, "require_github_settings", lambda: object())
    monkeypatch.setattr(connect_mod, "GitHubClient", lambda settings: FakeGH())
    monkeypatch.delenv("GITHUB_TEST_REPO", raising=False)
    assert connect_mod.run_connect(github=True, jira=False) == 0


def test_run_connect_missing_keys(monkeypatch):
    def boom():
        raise ValueError("Missing required env: GITHUB_TOKEN")

    monkeypatch.setattr(connect_mod, "require_github_settings", boom)
    assert connect_mod.run_connect(github=True, jira=False) == 1
