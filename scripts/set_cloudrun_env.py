"""Load .env and update Cloud Run env (never prints secret values)."""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SERVICE = "provepr"
REGION = "us-central1"
IMAGE = (
    "us-central1-docker.pkg.dev/kodifly-qa-automations/provepr/provepr:latest"
)

# Keys to push onto Cloud Run (values from local .env).
KEYS = [
    "PROVEPR_TRIGGER_SECRET",
    "GITHUB_TOKEN",
    "GITHUB_APP_ID",
    "GITHUB_APP_INSTALLATION_ID",
    "GITHUB_APP_PRIVATE_KEY",
    "JIRA_SERVER_URL",
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "SLACK_BOT_TOKEN",
    "SLACK_DEV_BOT_TOKEN",
    "SLACK_PM_BOT_TOKEN",
    "SLACK_DM_USER_ID",
    "HERMES_ENABLE_PROJECT_PLUGINS",
    "PROVEPR_HTTP_HOST",
    "PRD_GATE_BUG_SKIP_REPORTER_EMAILS",
    "PRD_GATE_SKIP_REPORTER_EMAILS",
    "PRD_GATE_SKIP_REPORTER_NAMES",
]


def yaml_escape(value: str) -> str:
    # Prefer literal block for multiline keys; otherwise double-quoted.
    if "\n" in value or "\r" in value:
        indented = "\n".join("  " + line for line in value.replace("\r\n", "\n").split("\n"))
        return f"|-\n{indented}"
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def gcloud_cmd() -> list[str]:
    # On Windows, `gcloud` is a .cmd/.ps1 wrapper — prefer the .cmd for subprocess.
    if os.name == "nt":
        return ["gcloud.cmd"]
    return ["gcloud"]


def main() -> int:
    vals = dotenv_values(ROOT / ".env")
    env: dict[str, str] = {}
    for key in KEYS:
        raw = (vals.get(key) or os.getenv(key) or "").strip()
        if not raw:
            continue
        if key == "GITHUB_APP_PRIVATE_KEY":
            raw = raw.strip('"').replace("\\n", "\n")
        env[key] = raw

    # Always set host/plugin defaults for Cloud Run.
    env["HERMES_ENABLE_PROJECT_PLUGINS"] = env.get("HERMES_ENABLE_PROJECT_PLUGINS") or "1"
    env["PROVEPR_HTTP_HOST"] = "0.0.0.0"

    if not env.get("PROVEPR_TRIGGER_SECRET"):
        env["PROVEPR_TRIGGER_SECRET"] = secrets.token_urlsafe(32)
        print("Generated new PROVEPR_TRIGGER_SECRET (also write it into local .env)")
        # Append/update local .env without printing the value.
        env_path = ROOT / ".env"
        text = env_path.read_text(encoding="utf-8")
        if "PROVEPR_TRIGGER_SECRET=" in text:
            lines = []
            for line in text.splitlines(keepends=True):
                if line.startswith("PROVEPR_TRIGGER_SECRET="):
                    lines.append(f"PROVEPR_TRIGGER_SECRET={env['PROVEPR_TRIGGER_SECRET']}\n")
                else:
                    lines.append(line)
            env_path.write_text("".join(lines), encoding="utf-8")
        else:
            with env_path.open("a", encoding="utf-8") as fh:
                fh.write(f"\nPROVEPR_TRIGGER_SECRET={env['PROVEPR_TRIGGER_SECRET']}\n")

    missing_required = [
        k
        for k in (
            "PROVEPR_TRIGGER_SECRET",
            "JIRA_SERVER_URL",
            "JIRA_EMAIL",
            "JIRA_API_TOKEN",
            "GOOGLE_API_KEY",
        )
        if not env.get(k)
    ]
    has_github = bool(env.get("GITHUB_TOKEN")) or (
        env.get("GITHUB_APP_ID")
        and env.get("GITHUB_APP_INSTALLATION_ID")
        and env.get("GITHUB_APP_PRIVATE_KEY")
    )
    if missing_required or not has_github:
        print("FAIL: missing required keys:", ", ".join(missing_required) or "GitHub auth")
        return 1

    with tempfile.NamedTemporaryFile(
        "w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        for key, value in env.items():
            fh.write(f"{key}: {yaml_escape(value)}\n")
        yaml_path = fh.name

    print(f"Updating Cloud Run env ({len(env)} keys; values not printed)...")
    gcloud = gcloud_cmd()
    cmd = [
        *gcloud,
        "run",
        "deploy",
        SERVICE,
        f"--image={IMAGE}",
        f"--region={REGION}",
        "--platform=managed",
        "--allow-unauthenticated",
        "--port=8080",
        "--memory=1Gi",
        "--cpu=1",
        "--timeout=300",
        "--max-instances=3",
        f"--env-vars-file={yaml_path}",
    ]
    try:
        result = subprocess.run(cmd, check=False)
    finally:
        Path(yaml_path).unlink(missing_ok=True)

    if result.returncode != 0:
        print("FAIL: gcloud run deploy exited", result.returncode)
        return result.returncode

    url = subprocess.check_output(
        [
            *gcloud,
            "run",
            "services",
            "describe",
            SERVICE,
            f"--region={REGION}",
            "--format=value(status.url)",
        ],
        text=True,
    ).strip()
    print("URL", url)
    # Write URL for smoke script (no secrets).
    (ROOT / ".cloudrun_url").write_text(url + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
