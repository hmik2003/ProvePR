"""Load configuration from environment / .env without exposing secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Sprint-gated keys: we only *require* them when that sprint starts.
SPRINT2_KEYS = (
    "GITHUB_TOKEN",
    "JIRA_SERVER_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
)
SPRINT3_KEYS = ("GOOGLE_API_KEY",)  # GEMINI_API_KEY accepted as alias
SPRINT4_KEYS = ("SLACK_WEBHOOK_URL",)

ALL_TRACKED_KEYS = SPRINT2_KEYS + SPRINT3_KEYS + SPRINT4_KEYS + ("GEMINI_API_KEY",)

# Cheap default for the supervisor's $5 budget (override with GEMINI_MODEL).
DEFAULT_GEMINI_MODEL = "gemini-flash-lite-latest"


@dataclass(frozen=True)
class KeyStatus:
    name: str
    present: bool


def project_root() -> Path:
    """Repo root (folder that contains PROJECT.md / requirements.txt)."""
    return Path(__file__).resolve().parents[2]


def load_env() -> Path | None:
    """Load `.env` from project root if it exists. Returns path loaded or None."""
    env_path = project_root() / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
        return env_path
    load_dotenv()
    return None


def key_present(name: str) -> bool:
    value = os.getenv(name)
    return bool(value and value.strip())


def gemini_key_present() -> bool:
    return key_present("GOOGLE_API_KEY") or key_present("GEMINI_API_KEY")


def status_for_keys(keys: tuple[str, ...]) -> list[KeyStatus]:
    return [KeyStatus(name=k, present=key_present(k)) for k in keys]


def missing_keys(keys: tuple[str, ...]) -> list[str]:
    return [k for k in keys if not key_present(k)]


@dataclass(frozen=True)
class GitHubSettings:
    token: str
    auth_mode: str = "pat"  # pat | app


def require_github_settings() -> GitHubSettings:
    """
    Prefer GitHub App credentials (KodiQA[bot]) when configured; else GITHUB_TOKEN PAT.

    App env (all three required together):
      GITHUB_APP_ID
      GITHUB_APP_INSTALLATION_ID
      GITHUB_APP_PRIVATE_KEY
    """
    load_env()
    app_id = (os.getenv("GITHUB_APP_ID") or "").strip()
    installation_id = (os.getenv("GITHUB_APP_INSTALLATION_ID") or "").strip()
    private_key = (os.getenv("GITHUB_APP_PRIVATE_KEY") or "").strip()
    if app_id and installation_id and private_key:
        from provepr.github_app import create_installation_access_token

        token = create_installation_access_token(
            app_id=app_id,
            private_key_pem=private_key,
            installation_id=installation_id,
        )
        return GitHubSettings(token=token, auth_mode="app")

    missing = missing_keys(("GITHUB_TOKEN",))
    if missing:
        raise ValueError(
            "Missing GitHub auth: set GITHUB_TOKEN, or GitHub App env "
            "(GITHUB_APP_ID + GITHUB_APP_INSTALLATION_ID + GITHUB_APP_PRIVATE_KEY)"
        )
    return GitHubSettings(token=os.environ["GITHUB_TOKEN"].strip(), auth_mode="pat")


@dataclass(frozen=True)
class JiraSettings:
    server_url: str
    email: str
    api_token: str


def normalize_jira_base_url(url: str) -> str:
    return url.strip().rstrip("/")


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


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str
    model: str


def require_gemini_settings() -> GeminiSettings:
    load_env()
    if not gemini_key_present():
        raise ValueError(
            "Missing required env: GOOGLE_API_KEY (or alias GEMINI_API_KEY)"
        )
    api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    model = (os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
    return GeminiSettings(api_key=api_key, model=model)


def bug_skip_reporter_emails() -> tuple[str, ...]:
    """
    Comma-separated reporter emails whose Bugs skip the soft quality gate.

    Env: PRD_GATE_BUG_SKIP_REPORTER_EMAILS
    Example: ibrahim.kayani@kodifly.com
    """
    load_env()
    raw = (os.getenv("PRD_GATE_BUG_SKIP_REPORTER_EMAILS") or "").strip()
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())
