from provepr.jira_key import (
    extract_jira_key,
    extract_jira_keys,
    primary_jira_key_from_title,
)


def test_extract_from_title():
    assert extract_jira_key("SX-2869: Add feature flag") == "SX-2869"


def test_extract_from_branch():
    assert extract_jira_key(None, "feature/PROJ-105-password-reset") == "PROJ-105"


def test_extract_prefers_earlier_text():
    assert extract_jira_key("ABC-1: x", "feature/ZZZ-9-y") == "ABC-1"


def test_extract_none():
    assert extract_jira_key("no ticket here", "feature/nope") is None


def test_extract_jira_keys_unique_order():
    assert extract_jira_keys("PROV-1 then PROV-2 and PROV-1") == ["PROV-1", "PROV-2"]


def test_primary_jira_key_exactly_one():
    assert primary_jira_key_from_title("PROV-9: stock") == ("PROV-9", ["PROV-9"])


def test_primary_jira_key_rejects_multiple():
    assert primary_jira_key_from_title("PROV-1 + PROV-2") == (None, ["PROV-1", "PROV-2"])
