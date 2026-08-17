from fastapi.testclient import TestClient

from provepr import server as server_mod
from provepr.pr_hook import decide_pr_ticket


def test_health():
    client = TestClient(server_mod.app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "provepr"
    assert "engine" in body
    assert "version" in body


def test_review_requires_secret(monkeypatch):
    monkeypatch.setattr(server_mod, "load_env", lambda: None)
    monkeypatch.setenv("PROVEPR_TRIGGER_SECRET", "secret-test")
    client = TestClient(server_mod.app)
    response = client.post("/v1/review", json={"post": False})
    assert response.status_code == 401


def test_review_calls_run_review(monkeypatch):
    monkeypatch.setattr(server_mod, "load_env", lambda: None)
    monkeypatch.setenv("PROVEPR_TRIGGER_SECRET", "secret-test")
    called = {}

    def fake_run_review(**kwargs):
        called.update(kwargs)
        return 0

    monkeypatch.setattr(server_mod, "run_review", fake_run_review)
    client = TestClient(server_mod.app)
    response = client.post(
        "/v1/review",
        headers={"Authorization": "Bearer secret-test"},
        json={
            "repo": "hmik2003/ProvePR",
            "pr": 1,
            "ticket": "SX-2869",
            "post": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert called["yes"] is True
    assert called["post"] is True
    assert called["pr"] == 1


def test_prd_gate_endpoint(monkeypatch):
    monkeypatch.setattr(server_mod, "load_env", lambda: None)
    monkeypatch.setenv("PROVEPR_TRIGGER_SECRET", "secret-test")

    class FakeResult:
        ticket_key = "PROV-10"
        verdict = "Ready"
        skipped = False
        skip_reason = ""
        present_count = 7
        mandatory_total = 7

    monkeypatch.setattr(
        server_mod,
        "execute_prd_gate",
        lambda **kw: type(
            "R",
            (),
            {
                "result": FakeResult(),
                "jira_comment_url": "http://jira/comment",
                "report": "ok",
                "slack_detail": "Slack OK",
            },
        )(),
    )
    client = TestClient(server_mod.app)
    response = client.post(
        "/v1/prd-gate",
        headers={"Authorization": "Bearer secret-test"},
        json={"ticket": "PROV-10"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["verdict"] == "Ready"
    assert body["jira_commented"] is True


def test_prd_gate_accepts_jira_automation_shape(monkeypatch):
    monkeypatch.setattr(server_mod, "load_env", lambda: None)
    monkeypatch.setenv("PROVEPR_TRIGGER_SECRET", "secret-test")
    seen = {}

    class FakeResult:
        ticket_key = "PROV-8"
        verdict = "Needs work"
        skipped = False
        skip_reason = ""
        present_count = 1
        mandatory_total = 7

    def fake_exec(**kw):
        seen.update(kw)
        return type(
            "R",
            (),
            {
                "result": FakeResult(),
                "jira_comment_url": "x",
                "report": "n",
                "slack_detail": "s",
            },
        )()

    monkeypatch.setattr(server_mod, "execute_prd_gate", fake_exec)
    client = TestClient(server_mod.app)
    response = client.post(
        "/v1/prd-gate",
        headers={"Authorization": "Bearer secret-test"},
        json={"issue": {"key": "PROV-8"}, "trigger": "in_progress"},
    )
    assert response.status_code == 200
    assert seen["ticket"] == "PROV-8"
    assert seen["trigger"] == "in_progress"
    assert response.json()["verdict"] == "Needs work"


def test_decide_pr_ticket_policy():
    assert decide_pr_ticket(title="PROV-18: limit").action == "review"
    assert decide_pr_ticket(title="PROV-1 and PROV-2").action == "skip"
    assert decide_pr_ticket(title="no key", branch="feature/PROV-9-x").ticket == "PROV-9"
    assert decide_pr_ticket(title="chore").action == "skip"


def test_pr_hook_reviews(monkeypatch):
    monkeypatch.setattr(server_mod, "load_env", lambda: None)
    monkeypatch.setenv("PROVEPR_TRIGGER_SECRET", "secret-test")
    seen = {}

    def fake_review(**kwargs):
        seen.update(kwargs)
        return 0

    monkeypatch.setattr(server_mod, "run_review", fake_review)
    client = TestClient(server_mod.app)
    response = client.post(
        "/v1/pr-hook",
        headers={"Authorization": "Bearer secret-test"},
        json={
            "repo": "hmik2003/provepr-demo-shop",
            "pr": 13,
            "title": "PROV-18: Catalog limit",
            "post": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "review"
    assert body["ticket_key"] == "PROV-18"
    assert seen["ticket"] == "PROV-18"
    assert seen["post"] is True


def test_pr_hook_skips(monkeypatch):
    monkeypatch.setattr(server_mod, "load_env", lambda: None)
    monkeypatch.setenv("PROVEPR_TRIGGER_SECRET", "secret-test")
    called = {}

    def fake_skip(**kwargs):
        called.update(kwargs)
        return 0

    monkeypatch.setattr(server_mod, "run_skip_notify", fake_skip)
    client = TestClient(server_mod.app)
    response = client.post(
        "/v1/pr-hook",
        headers={"Authorization": "Bearer secret-test"},
        json={
            "repo": "hmik2003/provepr-demo-shop",
            "pr": 12,
            "title": "chore: no ticket",
            "post": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["action"] == "skip"
    assert called["reason"] == "none"
