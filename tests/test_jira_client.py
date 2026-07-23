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


def test_jira_client_exposes_only_allowed_methods():
    """Security: no issue create/edit/transition; comments allowed for PRD gate only."""
    allowed = {
        "__init__",
        "close",
        "__enter__",
        "__exit__",
        "get_myself",
        "get_issue",
        "get_subtasks",
        "get_development_pull_requests",
        "add_comment",
    }
    methods = {
        name
        for name, obj in vars(JiraClient).items()
        if callable(obj) and (not name.startswith("_") or name in allowed)
    }
    assert methods <= allowed
    assert {
        "get_myself",
        "get_issue",
        "get_subtasks",
        "get_development_pull_requests",
        "add_comment",
    } <= methods
    forbidden = {
        "create_issue",
        "update_issue",
        "delete_issue",
        "transition_issue",
    }
    assert not (forbidden & set(dir(JiraClient)))


@respx.mock
def test_get_subtasks_fetches_children():
    respx.get(
        "https://acme.atlassian.net/rest/api/3/issue/PROV-1",
        params={"fields": "summary,subtasks"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "key": "PROV-1",
                "fields": {"summary": "Parent", "subtasks": [{"key": "PROV-2"}]},
            },
        )
    )
    respx.get(
        "https://acme.atlassian.net/rest/api/3/issue/PROV-2",
        params={"fields": "summary,description,status"},
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "key": "PROV-2",
                "fields": {
                    "summary": "Child",
                    "description": "AC",
                    "status": {"name": "To Do"},
                },
            },
        )
    )
    client = JiraClient(_settings())
    children = client.get_subtasks("PROV-1")
    assert len(children) == 1
    assert children[0]["key"] == "PROV-2"


@respx.mock
def test_get_development_pull_requests_ok():
    respx.get("https://acme.atlassian.net/rest/dev-status/latest/issue/detail").mock(
        return_value=httpx.Response(
            200,
            json={
                "detail": [
                    {
                        "pullRequests": [
                            {
                                "id": "42",
                                "url": "https://github.com/o/r/pull/42",
                                "name": "Pull request #42",
                            }
                        ]
                    }
                ]
            },
        )
    )
    client = JiraClient(_settings())
    prs, err = client.get_development_pull_requests({"id": "100", "key": "PROV-1"})
    assert err is None
    assert len(prs) == 1
    assert prs[0]["id"] == "42"


@respx.mock
def test_get_development_pull_requests_forbidden():
    respx.get("https://acme.atlassian.net/rest/dev-status/latest/issue/detail").mock(
        return_value=httpx.Response(403, json={})
    )
    client = JiraClient(_settings())
    prs, err = client.get_development_pull_requests({"id": "100", "key": "PROV-1"})
    assert prs == []
    assert err is not None
    assert "Development" in err


@respx.mock
def test_add_comment_ok():
    respx.post("https://acme.atlassian.net/rest/api/3/issue/PROV-10/comment").mock(
        return_value=httpx.Response(
            201,
            json={"id": "100", "self": "https://acme.atlassian.net/rest/api/3/issue/100/comment/100"},
        )
    )
    client = JiraClient(_settings())
    posted = client.add_comment(
        "PROV-10",
        {"type": "doc", "version": 1, "content": []},
    )
    assert posted["id"] == "100"
