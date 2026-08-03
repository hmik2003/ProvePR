"""Load KodiQA GitHub App private key into .env (never prints the key).

Usage:
  python scripts/load_kodiqa_pem.py "C:\\Users\\HP\\Downloads\\kodiqa.YYYY-MM-DD.private-key.pem"
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_kodiqa_pem.py <path-to-private-key.pem>")
        return 1
    pem_path = Path(sys.argv[1]).expanduser().resolve()
    if not pem_path.is_file():
        print(f"File not found: {pem_path}")
        return 1
    pem = pem_path.read_text(encoding="utf-8").strip()
    if "BEGIN" not in pem or "PRIVATE KEY" not in pem:
        print("That file does not look like a GitHub App private key PEM.")
        return 1
    # Store with escaped newlines for single-line .env friendliness
    escaped = pem.replace("\r\n", "\n").replace("\n", "\\n")
    env_path = Path(__file__).resolve().parents[1] / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    key = "GITHUB_APP_PRIVATE_KEY"
    out: list[str] = []
    seen = False
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            out.append(f'{key}="{escaped}"')
            seen = True
        else:
            out.append(line)
    if not seen:
        out.append(f'{key}="{escaped}"')
    env_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"Loaded private key from {pem_path.name} into .env as GITHUB_APP_PRIVATE_KEY")
    print("Do not commit .env. Next: add the same PEM to GitHub Actions secret KODIQA_APP_PRIVATE_KEY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
