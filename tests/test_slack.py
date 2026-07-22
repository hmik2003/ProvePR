import httpx
import respx

from provepr import slack as slack_mod


def test_notify_slack_stub(monkeypatch):
    monkeypatch.setattr(slack_mod, "load_env", lambda: None)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    result = slack_mod.notify_slack("hi")
    assert result.posted is False
    assert "stub" in result.detail.lower()


@respx.mock
def test_notify_slack_posts(monkeypatch):
    monkeypatch.setattr(slack_mod, "load_env", lambda: None)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/X")
    respx.post("https://hooks.slack.com/services/T/B/X").mock(
        return_value=httpx.Response(200, text="ok")
    )
    result = slack_mod.notify_slack("hi")
    assert result.posted is True
