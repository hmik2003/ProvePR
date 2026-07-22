from provepr.config import SPRINT2_KEYS, missing_keys, status_for_keys


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
