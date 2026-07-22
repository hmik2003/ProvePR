# Sprint 2 — GitHub + Jira Read Connections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove ProvePR can authenticate and read from GitHub and Jira using local `.env` secrets, via a working `connect` CLI.

**Architecture:** Thin HTTP clients (`httpx`) for GitHub REST and Jira Cloud REST. Config loads required Sprint 2 keys and fails clearly when missing. CLI command `python -m provepr connect` runs both checks (or `--github` / `--jira` alone). No PR diff / ticket PRD parsing yet — that is Sprint 3. Secrets are never printed.

**Tech Stack:** Python 3.11+, `httpx`, `python-dotenv`, `pytest` (+ `respx` or `httpx` MockTransport for tests)

## Global Constraints

- Never commit `.env` or real secrets; never print token values
- Read-only access only (GitHub: read repo/user; Jira: browse/read issues)
- Personal GitHub `hmik2003` first; any readable Jira Cloud board
- Product name **ProvePR** / package `provepr`
- One working product increment this sprint: live (or mock-tested) connect CLI
- Supervisor: **not required** unless your Jira account cannot create an API token or lacks browse permission on the test project

## File Structure

| File | Responsibility |
|------|----------------|
| `src/provepr/config.py` | Load env; require Sprint 2 keys; expose typed settings helpers |
| `src/provepr/github_client.py` | Authenticated GitHub GET helpers (`whoami`, optional repo peek) |
| `src/provepr/jira_client.py` | Authenticated Jira GET helpers (`myself`, optional issue peek) |
| `src/provepr/connect.py` | Orchestrate connect checks; format human-readable OK/FAIL output |
| `src/provepr/__main__.py` | Add `connect` subcommand |
| `src/provepr/smoke.py` | Point next-sprint messaging at Sprint 3 after connect exists |
| `tests/test_github_client.py` | Mocked GitHub auth + error paths |
| `tests/test_jira_client.py` | Mocked Jira auth + error paths |
| `tests/test_connect.py` | Connect orchestration with mocked clients |
| `requirements.txt` | Add `httpx`, `respx` |
| `.env.example` | Document optional `GITHUB_TEST_REPO`, `JIRA_TEST_TICKET` |
| `README.md` / `PROJECT.md` | Sprint 2 runbook + phase status |

---

### Task 1: Settings helpers for Sprint 2 keys

**Files:**
- Modify: `src/provepr/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: existing `load_env`, `key_present`, `SPRINT2_KEYS`, `missing_keys`
- Produces:
  - `class GitHubSettings` with `token: str`
  - `class JiraSettings` with `server_url: str`, `email: str`, `api_token: str`
  - `def require_github_settings() -> GitHubSettings` (raises `ValueError` listing missing keys)
  - `def require_jira_settings() -> JiraSettings` (raises `ValueError` listing missing keys)
  - `def normalize_jira_base_url(url: str) -> str` (strip trailing slash)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py — add:

def test_require_github_settings_missing(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    import provepr.config as config
    try:
        config.require_github_settings()
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "GITHUB_TOKEN" in str(exc)


def test_require_github_settings_ok(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    from provepr.config import require_github_settings
    settings = require_github_settings()
    assert settings.token == "ghp_test"


def test_require_jira_settings_ok(monkeypatch):
    monkeypatch.setenv("JIRA_SERVER_URL", "https://acme.atlassian.net/")
    monkeypatch.setenv("JIRA_EMAIL", "a@b.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "tok")
    from provepr.config import require_jira_settings
    settings = require_jira_settings()
    assert settings.server_url == "https://acme.atlassian.net"
    assert settings.email == "a@b.com"
    assert settings.api_token == "tok"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -q`
Expected: FAIL — `require_github_settings` / `require_jira_settings` not defined

- [ ] **Step 3: Implement settings helpers**

Add to `src/provepr/config.py`:

```python
@dataclass(frozen=True)
class GitHubSettings:
    token: str


@dataclass(frozen=True)
class JiraSettings:
    server_url: str
    email: str
    api_token: str


def normalize_jira_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def require_github_settings() -> GitHubSettings:
    load_env()
    missing = missing_keys(("GITHUB_TOKEN",))
    if missing:
        raise ValueError(f"Missing required env: {', '.join(missing)}")
    return GitHubSettings(token=os.environ["GITHUB_TOKEN"].strip())


def require_jira_settings() -> JiraSettings:
    load_env()
    missing = missing_keys(("JIRA_SERVER_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"))
    if missing:
        raise ValueError(f"Missing required env: {', '.join(missing)}")
    return JiraSettings(
        server_url=normalize_jira_base_url(os.environ["JIRA_SERVER_URL"]),
        email=os.environ["JIRA_EMAIL"].strip(),
        api_token=os.environ["JIRA_API_TOKEN"].strip(),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/provepr/config.py tests/test_config.py
git commit -m "feat: add GitHub and Jira settings helpers for Sprint 2"
```

---

### Task 2: GitHub read client

**Files:**
- Create: `src/provepr/github_client.py`
- Create: `tests/test_github_client.py`
- Modify: `requirements.txt` (add `httpx>=0.27.0` and `respx>=0.21.0`)

**Interfaces:**
- Consumes: `GitHubSettings`
- Produces:
  - `class GitHubClient` with `__init__(self, settings: GitHubSettings, client: httpx.Client | None = None)`
  - `def get_authenticated_user(self) -> dict` → `GET https://api.github.com/user`
  - `def get_repo(self, full_name: str) -> dict` → `GET https://api.github.com/repos/{full_name}`
  - Raises `httpx.HTTPStatusError` on non-2xx (caller formats message; never include token)

- [ ] **Step 1: Add dependencies**

```text
python-dotenv>=1.0.1
pytest>=8.0.0
httpx>=0.27.0
respx>=0.21.0
```

Run: `pip install -r requirements.txt`

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_github_client.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_github_client.py -q`
Expected: FAIL — module not found

- [ ] **Step 4: Implement GitHub client**

```python
# src/provepr/github_client.py
from __future__ import annotations

import httpx

from provepr.config import GitHubSettings

API_ROOT = "https://api.github.com"


class GitHubClient:
    def __init__(
        self,
        settings: GitHubSettings,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=API_ROOT,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {settings.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "ProvePR",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GitHubClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_authenticated_user(self) -> dict:
        response = self._client.get("/user")
        response.raise_for_status()
        return response.json()

    def get_repo(self, full_name: str) -> dict:
        response = self._client.get(f"/repos/{full_name}")
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_github_client.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/provepr/github_client.py tests/test_github_client.py
git commit -m "feat: add read-only GitHub client"
```

---

### Task 3: Jira read client

**Files:**
- Create: `src/provepr/jira_client.py`
- Create: `tests/test_jira_client.py`

**Interfaces:**
- Consumes: `JiraSettings`
- Produces:
  - `class JiraClient` with `__init__(self, settings: JiraSettings, client: httpx.Client | None = None)`
  - `def get_myself(self) -> dict` → `GET {base}/rest/api/3/myself`
  - `def get_issue(self, key: str) -> dict` → `GET {base}/rest/api/3/issue/{key}` (fields limited later; full JSON OK for Sprint 2)
  - Basic auth: email + API token (httpx `auth=(email, api_token)`)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_jira_client.py
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
        return_value=httpx.Response(200, json={"displayName": "QA Lead", "accountId": "x"})
    )
    client = JiraClient(_settings())
    me = client.get_myself()
    assert me["displayName"] == "QA Lead"


@respx.mock
def test_get_issue_ok():
    respx.get("https://acme.atlassian.net/rest/api/3/issue/PROJ-1").mock(
        return_value=httpx.Response(200, json={"key": "PROJ-1", "fields": {"summary": "Demo"}})
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_jira_client.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Implement Jira client**

```python
# src/provepr/jira_client.py
from __future__ import annotations

import httpx

from provepr.config import JiraSettings


class JiraClient:
    def __init__(
        self,
        settings: JiraSettings,
        client: httpx.Client | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=settings.server_url,
            auth=(settings.email, settings.api_token),
            headers={
                "Accept": "application/json",
                "User-Agent": "ProvePR",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> JiraClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def get_myself(self) -> dict:
        response = self._client.get("/rest/api/3/myself")
        response.raise_for_status()
        return response.json()

    def get_issue(self, key: str) -> dict:
        response = self._client.get(f"/rest/api/3/issue/{key}")
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_jira_client.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/provepr/jira_client.py tests/test_jira_client.py
git commit -m "feat: add read-only Jira client"
```

---

### Task 4: `connect` CLI (working product)

**Files:**
- Create: `src/provepr/connect.py`
- Create: `tests/test_connect.py`
- Modify: `src/provepr/__main__.py`
- Modify: `src/provepr/smoke.py` (next-sprint line → Sprint 3)
- Modify: `README.md`, `PROJECT.md`, `.env.example` as needed

**Interfaces:**
- Consumes: `require_github_settings`, `require_jira_settings`, `GitHubClient`, `JiraClient`, `os.getenv` for optional `GITHUB_TEST_REPO`, `JIRA_TEST_TICKET`
- Produces:
  - `def run_connect(*, github: bool = True, jira: bool = True) -> int`
  - Exit `0` if all requested checks succeed; `1` if any fail
  - Prints login/displayName and optional repo/issue summary — never tokens

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_connect.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_connect.py -q`
Expected: FAIL — module not found

- [ ] **Step 3: Implement connect + CLI wiring**

`connect.py` should:
1. Load env once
2. For GitHub: require settings → `get_authenticated_user` → print `GitHub OK as @{login}`; if `GITHUB_TEST_REPO` set, also `get_repo` and print full_name
3. For Jira: require settings → `get_myself` → print `Jira OK as {displayName}`; if `JIRA_TEST_TICKET` set, also `get_issue` and print key + summary
4. Catch `ValueError` (missing env) and `httpx.HTTPStatusError` / `httpx.RequestError`; print short reason without secrets
5. End with `=== Sprint 2 OK ===` only when all requested checks pass

Wire `__main__.py`:

```python
connect_parser = sub.add_parser("connect", help="Sprint 2: verify GitHub + Jira read access")
connect_parser.add_argument("--github", action="store_true", help="Only check GitHub")
connect_parser.add_argument("--jira", action="store_true", help="Only check Jira")
# If neither flag: check both
```

- [ ] **Step 4: Run unit tests**

Run: `pytest -q`
Expected: all PASS

- [ ] **Step 5: Live check (human credentials required)**

Prerequisites: `.env` filled with Sprint 2 keys (see human checklist below).

```powershell
$env:PYTHONPATH = "src"
python -m provepr connect
```

Expected: `GitHub OK`, `Jira OK`, `=== Sprint 2 OK ===`

Optional deeper peek:

```env
GITHUB_TEST_REPO=hmik2003/ProvePR
JIRA_TEST_TICKET=PROJ-123
```

Then re-run `python -m provepr connect`.

- [ ] **Step 6: Update docs**

- `README.md`: Sprint 2 section — setup keys, `connect` command
- `PROJECT.md`: mark Sprint 2 Done; next = Sprint 3; phase log entry
- `.env.example`: uncomment/document optional test targets

- [ ] **Step 7: Commit**

```bash
git add src/provepr/connect.py src/provepr/__main__.py src/provepr/smoke.py tests/test_connect.py README.md PROJECT.md .env.example
git commit -m "feat: add connect CLI for GitHub and Jira read checks"
```

**Done when:** `python -m provepr connect` exits 0 against real GitHub + Jira (or documented skip if a partner cannot obtain Jira read yet), and unit tests pass without live network.

---

## Human credential checklist (do before Task 4 live check)

### A. GitHub PAT — you (no supervisor)

1. GitHub → Settings → Developer settings → Personal access tokens
2. Create a fine-grained or classic token with at least: **read access to repos** you will test (classic: `repo` for private, or `public_repo` for public-only)
3. Put it in `.env` as `GITHUB_TOKEN=...` (never paste into chat)

### B. Jira API token — you (supervisor only if blocked)

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens → Create API token
2. In `.env` set:
   - `JIRA_SERVER_URL=https://YOUR.atlassian.net`
   - `JIRA_EMAIL=` the Atlassian account email
   - `JIRA_API_TOKEN=` the token
3. **Involve supervisor only if:** you cannot create an API token, or your account cannot browse the Jira project you want to use for tests

### C. Optional test targets

- `GITHUB_TEST_REPO=owner/name` — any repo your PAT can read
- `JIRA_TEST_TICKET=KEY-123` — any issue your account can view
