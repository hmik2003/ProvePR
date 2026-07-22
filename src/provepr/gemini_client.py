"""One-shot native Gemini generateContent client (cost-safe: no retries)."""

from __future__ import annotations

import httpx

from provepr.config import GeminiSettings

API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class GeminiClient:
    """Single-request Gemini client — never loops or auto-retries."""

    def __init__(
        self,
        settings: GeminiSettings,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=API_ROOT,
            timeout=90.0,
            headers={"User-Agent": "ProvePR"},
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> GeminiClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def generate_text(self, *, system: str, user: str) -> str:
        """Call generateContent exactly once. Raises on HTTP errors."""
        model = self._settings.model
        path = f"/models/{model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }
        response = self._client.post(
            path,
            params={"key": self._settings.api_key},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return _extract_text(data)


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    texts = [str(p.get("text") or "") for p in parts if p.get("text")]
    text = "\n".join(t for t in texts if t).strip()
    if not text:
        raise ValueError("Gemini returned empty text")
    return text
