import httpx
import respx

from provepr.config import JiraSettings
from provepr.jira_client import JiraClient


def _settings() -> JiraSettings:
    return JiraSettings(
        server_url="https://acme.atlassian.net",
        email="a@b.com",
        api_token="tok",
    )


@respx.mock
def test_get_myself_ok():
    respx.get("https://acme.atlassian.net/rest/api/3/myself").mock(
        return_value=httpx.Response(
            200, json={"displayName": "QA Lead", "accountId": "x"}
        )
    )
    client = JiraClient(_settings())
    me = client.get_myself()
    assert me["displayName"] == "QA Lead"


@respx.mock
def test_get_issue_ok():
    respx.get("https://acme.atlassian.net/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(
            200, json={"key": "PROJ-1", "fields": {"summary": "Demo"}}
        )
    )
    client = JiraClient(_settings())
    issue = client.get_issue("PROJ-1")
    assert issue["key"] == "PROJ-1"


@respx.mock
def test_get_myself_401():
    respx.get("https://acme.atlassian.net/rest/api/3/myself").mock(
        return_value=httpx.Response(401, json={"errorMessages": ["Unauthorized"]})
    )
    client = JiraClient(_settings())
    try:
        client.get_myself()
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 401


def test_jira_client_exposes_only_read_methods():
    """Security: product must not grow accidental Jira write helpers."""
    allowed = {
        "__init__",
        "close",
        "__enter__",
        "__exit__",
        "get_myself",
        "get_issue",
    }
    methods = {
        name
        for name, obj in vars(JiraClient).items()
        if callable(obj) and (not name.startswith("_") or name in allowed)
    }
    assert methods <= allowed
    assert {"get_myself", "get_issue"} <= methods
    forbidden = {
        "create_issue",
        "update_issue",
        "delete_issue",
        "add_comment",
        "transition_issue",
    }
    assert not (forbidden & set(dir(JiraClient)))
