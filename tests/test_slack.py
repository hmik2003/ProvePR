import httpx
import respx

from provepr import slack as slack_mod


def test_notify_slack_stub(monkeypatch):
    monkeypatch.setattr(slack_mod, "load_env", lambda: None)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_DM_USER_ID", raising=False)
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    result = slack_mod.notify_slack("hi")
    assert result.posted is False
    assert "stub" in result.detail.lower()


@respx.mock
def test_notify_slack_dm(monkeypatch):
    monkeypatch.setattr(slack_mod, "load_env", lambda: None)
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_DM_USER_ID", "U123")
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)

    respx.post("https://slack.com/api/conversations.open").mock(
        return_value=httpx.Response(200, json={"ok": True, "channel": {"id": "D999"}})
    )
    respx.post("https://slack.com/api/chat.postMessage").mock(
        return_value=httpx.Response(200, json={"ok": True, "ts": "1.2"})
    )

    result = slack_mod.notify_slack("hi")
    assert result.posted is True
    assert "DM" in result.detail


@respx.mock
def test_notify_slack_webhook_fallback(monkeypatch):
    monkeypatch.setattr(slack_mod, "load_env", lambda: None)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SLACK_DM_USER_ID", raising=False)
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/X")
    respx.post("https://hooks.slack.com/services/T/B/X").mock(
        return_value=httpx.Response(200, text="ok")
    )
    result = slack_mod.notify_slack("hi")
    assert result.posted is True
    assert "webhook" in result.detail.lower()
