import httpx
import respx

from provepr.config import GeminiSettings
from provepr.gemini_client import GeminiClient


@respx.mock
def test_generate_text_ok():
    respx.post(
        url__regex=r"https://generativelanguage\.googleapis\.com/v1beta/models/.+:generateContent"
    ).mock(
        return_value=httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "Verdict: Partial"}]}}
                ]
            },
        )
    )
    client = GeminiClient(GeminiSettings(api_key="k", model="gemini-2.5-flash-lite"))
    text = client.generate_text(system="sys", user="usr")
    assert "Partial" in text


@respx.mock
def test_generate_text_http_error():
    respx.post(
        url__regex=r"https://generativelanguage\.googleapis\.com/v1beta/models/.+:generateContent"
    ).mock(return_value=httpx.Response(429, json={"error": {"message": "quota"}}))
    client = GeminiClient(GeminiSettings(api_key="k", model="gemini-2.5-flash-lite"))
    try:
        client.generate_text(system="sys", user="usr")
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError as exc:
        assert exc.response.status_code == 429
