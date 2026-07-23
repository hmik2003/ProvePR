from provepr.skip_notify import (
    format_skip_message,
    format_skip_pr_comment,
    run_skip_notify,
)


def test_format_skip_message_no_key():
    text = format_skip_message(
        repo="hmik2003/provepr-demo-shop",
        pr=12,
        reason="none",
        title="chore: no ticket",
        pr_url="https://github.com/hmik2003/provepr-demo-shop/pull/12",
    )
    assert "skipped review" in text.lower() or "Skip" in text or "skipped" in text
    assert "provepr-demo-shop#12" in text
    assert "No Jira ticket key" in text
    assert "Gemini" in text


def test_format_skip_message_multiple():
    text = format_skip_message(
        repo="o/r",
        pr=1,
        reason="multiple",
        detail="PROV-1,PROV-2",
    )
    assert "multiple" in text.lower()
    assert "PROV-1,PROV-2" in text


def test_format_skip_pr_comment_none():
    body = format_skip_pr_comment(reason="none")
    assert "ProvePR skipped" in body
    assert "no Gemini" in body.lower() or "Gemini" in body


def test_run_skip_notify_slack_and_comment(monkeypatch):
    calls = {"slack": 0, "comment": 0}

    class FakeGH:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def create_issue_comment(self, repo, pr, body):
            calls["comment"] += 1
            assert "ProvePR skipped" in body
            return {"html_url": "http://comment"}

    monkeypatch.setattr("provepr.skip_notify.load_env", lambda: None)
    monkeypatch.setattr(
        "provepr.skip_notify.notify_slack",
        lambda text: (
            calls.__setitem__("slack", calls["slack"] + 1),
            type("R", (), {"posted": True, "detail": "Slack OK: DM delivered"})(),
        )[1],
    )
    monkeypatch.setattr(
        "provepr.skip_notify.require_github_settings", lambda: object()
    )
    monkeypatch.setattr("provepr.skip_notify.GitHubClient", lambda s: FakeGH())

    assert (
        run_skip_notify(
            repo="hmik2003/provepr-demo-shop",
            pr=12,
            reason="none",
            title="chore",
            pr_url="http://pr",
            comment=True,
        )
        == 0
    )
    assert calls["slack"] == 1
    assert calls["comment"] == 1
