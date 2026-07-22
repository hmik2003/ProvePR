import httpx
import respx

from provepr.config import GitHubSettings
from provepr.github_client import GitHubClient


@respx.mock
def test_get_authenticated_user_ok():
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(200, json={"login": "hmik2003", "id": 1})
    )
    client = GitHubClient(GitHubSettings(token="ghp_test"))
    user = client.get_authenticated_user()
    assert user["login"] == "hmik2003"


@respx.mock
def test_get_repo_ok():
    respx.get("https://api.github.com/repos/hmik2003/ProvePR").mock(
        return_value=httpx.Response(200, json={"full_name": "hmik2003/ProvePR"})
    )
    client = GitHubClient(GitHubSettings(token="ghp_test"))
    repo = client.get_repo("hmik2003/ProvePR")
    assert repo["full_name"] == "hmik2003/ProvePR"


@respx.mock
def test_get_authenticated_user_401():
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )
    client = GitHubClient(GitHubSettings(token="bad"))
    try:
        client.get_authenticated_user()
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 401


@respx.mock
def test_get_pull_request_ok():
    respx.get("https://api.github.com/repos/hmik2003/ProvePR/pulls/1").mock(
        return_value=httpx.Response(
            200,
            json={
                "number": 1,
                "title": "DEMO-1: sample",
                "html_url": "https://github.com/hmik2003/ProvePR/pull/1",
            },
        )
    )
    client = GitHubClient(GitHubSettings(token="ghp_test"))
    pr = client.get_pull_request("hmik2003/ProvePR", 1)
    assert pr["number"] == 1
    assert pr["title"] == "DEMO-1: sample"


@respx.mock
def test_get_pull_request_diff_ok():
    diff_body = "diff --git a/x b/x\n+hello\n"
    respx.get("https://api.github.com/repos/hmik2003/ProvePR/pulls/1").mock(
        return_value=httpx.Response(
            200,
            text=diff_body,
            headers={"Content-Type": "application/vnd.github.diff"},
        )
    )
    client = GitHubClient(GitHubSettings(token="ghp_test"))
    diff = client.get_pull_request_diff("hmik2003/ProvePR", 1)
    assert "hello" in diff
