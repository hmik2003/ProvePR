from provepr.config import (
    SPRINT2_KEYS,
    missing_keys,
    require_github_settings,
    require_jira_settings,
    status_for_keys,
)


def test_sprint2_key_list_is_stable():
    assert "GITHUB_TOKEN" in SPRINT2_KEYS
    assert "JIRA_API_TOKEN" in SPRINT2_KEYS


def test_status_for_keys_returns_one_row_per_key(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    rows = status_for_keys(("GITHUB_TOKEN",))
    assert len(rows) == 1
    assert rows[0].name == "GITHUB_TOKEN"
    assert rows[0].present is False


def test_missing_keys_detects_empty(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    assert missing_keys(("GITHUB_TOKEN",)) == ["GITHUB_TOKEN"]


def test_require_github_settings_missing(monkeypatch):
    monkeypatch.setattr("provepr.config.load_env", lambda: None)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    try:
        require_github_settings()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "GITHUB_TOKEN" in str(exc)


def test_require_github_settings_ok(monkeypatch):
    monkeypatch.setattr("provepr.config.load_env", lambda: None)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    settings = require_github_settings()
    assert settings.token == "ghp_test"


def test_require_jira_settings_ok(monkeypatch):
    monkeypatch.setattr("provepr.config.load_env", lambda: None)
    monkeypatch.setenv("JIRA_SERVER_URL", "https://acme.atlassian.net/")
    monkeypatch.setenv("JIRA_EMAIL", "a@b.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "tok")
    settings = require_jira_settings()
    assert settings.server_url == "https://acme.atlassian.net"
    assert settings.email == "a@b.com"
    assert settings.api_token == "tok"
