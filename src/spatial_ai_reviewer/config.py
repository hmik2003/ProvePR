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
SPRINT3_KEYS = ("GOOGLE_API_KEY",)  # GEMINI_API_KEY is accepted as alias later
SPRINT4_KEYS = ("SLACK_WEBHOOK_URL",)

ALL_TRACKED_KEYS = SPRINT2_KEYS + SPRINT3_KEYS + SPRINT4_KEYS + ("GEMINI_API_KEY",)


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
    # Still allow ambient process env (CI later)
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
