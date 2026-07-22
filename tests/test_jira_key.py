from provepr.jira_key import extract_jira_key


def test_extract_from_title():
    assert extract_jira_key("SX-2869: Add feature flag") == "SX-2869"


def test_extract_from_branch():
    assert extract_jira_key(None, "feature/PROJ-105-password-reset") == "PROJ-105"


def test_extract_prefers_earlier_text():
    assert extract_jira_key("ABC-1: x", "feature/ZZZ-9-y") == "ABC-1"


def test_extract_none():
    assert extract_jira_key("no ticket here", "feature/nope") is None
