from provepr.jira_text import adf_to_text, issue_prd_text


def test_adf_to_text_simple_doc():
    doc = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Accept reset emails."}],
            }
        ],
    }
    assert "Accept reset emails." in adf_to_text(doc)


def test_issue_prd_text_string_description():
    issue = {
        "fields": {
            "summary": "Password reset",
            "description": "Users can reset via email.",
        }
    }
    text = issue_prd_text(issue)
    assert "Summary: Password reset" in text
    assert "Users can reset via email." in text


def test_issue_prd_text_adf_description():
    issue = {
        "fields": {
            "summary": "Login",
            "description": {
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "Show error on bad password."}],
                    }
                ],
            },
        }
    }
    text = issue_prd_text(issue)
    assert "Summary: Login" in text
    assert "Show error on bad password." in text


def test_issue_prd_text_empty():
    assert issue_prd_text({"fields": {}}) == ""
