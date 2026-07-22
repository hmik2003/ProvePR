from fastapi.testclient import TestClient

from provepr import server as server_mod


def test_health():
    client = TestClient(server_mod.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
