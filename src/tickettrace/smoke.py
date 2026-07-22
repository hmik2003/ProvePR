"""Sprint 1 smoke check — proves the local product runs without live APIs."""

from __future__ import annotations

import sys

from tickettrace import __version__
from tickettrace.config import (
    SPRINT2_KEYS,
    SPRINT3_KEYS,
    SPRINT4_KEYS,
    gemini_key_present,
    load_env,
    project_root,
    status_for_keys,
)


def _print_key_group(title: str, keys: tuple[str, ...]) -> None:
    print(f"\n{title}")
    for item in status_for_keys(keys):
        mark = "SET" if item.present else "missing"
        print(f"  [{mark}] {item.name}")


def run_smoke() -> int:
    root = project_root()
    env_path = load_env()

    print("=== TicketTrace — Sprint 1 Smoke ===")
    print(f"Package version : {__version__}")
    print(f"Project root    : {root}")
    print(f"Python          : {sys.version.split()[0]}")
    if env_path:
        print(f".env            : found at {env_path} (values never printed)")
    else:
        print(".env            : not found yet — copy .env.example to .env when ready")

    _print_key_group("Sprint 2 keys (GitHub + Jira) — needed next:", SPRINT2_KEYS)
    _print_key_group("Sprint 3 keys (Gemini for Hermes):", SPRINT3_KEYS)
    if gemini_key_present() and not status_for_keys(SPRINT3_KEYS)[0].present:
        print("  [SET] GEMINI_API_KEY (alias — OK for Hermes)")
    _print_key_group("Sprint 4 keys (Slack):", SPRINT4_KEYS)

    print("\n=== Sprint 1 OK ===")
    print("Working product this sprint: local package + smoke CLI.")
    print("Next sprint: connect GitHub + Jira (read-only).")
    print("You do NOT need keys for Sprint 1 to pass.")
    return 0
