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
