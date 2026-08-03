"""Set KODIQA_* Actions secrets on ProvePR + provepr-demo-shop. Never prints secret values."""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from nacl import encoding, public

ROOT = Path(__file__).resolve().parents[1]
REPOS = ["hmik2003/ProvePR", "hmik2003/provepr-demo-shop"]


def encrypt_secret(public_key: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(sealed).decode("utf-8")


def main() -> int:
    load_dotenv(ROOT / ".env")
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        print("FAIL: GITHUB_TOKEN missing in .env (PAT with repo admin needed for secrets API)")
        return 1

    app_id = (os.getenv("GITHUB_APP_ID") or "4469810").strip()
    pem = (os.getenv("GITHUB_APP_PRIVATE_KEY") or "").strip().replace("\\n", "\n")
    if not pem or "BEGIN" not in pem:
        pem_path = Path.home() / "Downloads" / "kodiqa.2026-08-02.private-key.pem"
        if not pem_path.is_file():
            print(f"FAIL: private key not found at {pem_path}")
            return 1
        pem = pem_path.read_text(encoding="utf-8")

    secrets = {
        "KODIQA_APP_ID": app_id,
        "KODIQA_APP_PRIVATE_KEY": pem,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "KodiQA-setup",
    }

    ok = True
    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=60.0) as client:
        me = client.get("/user")
        if me.status_code != 200:
            print(f"FAIL: auth {me.status_code} — need a classic/fine-grained PAT with admin on repos")
            return 1
        print(f"Authenticated as {me.json().get('login')}")

        for repo in REPOS:
            pk_resp = client.get(f"/repos/{repo}/actions/secrets/public-key")
            if pk_resp.status_code != 200:
                print(f"FAIL {repo} public-key: HTTP {pk_resp.status_code}")
                ok = False
                continue
            pk = pk_resp.json()
            for name, value in secrets.items():
                enc = encrypt_secret(pk["key"], value)
                put = client.put(
                    f"/repos/{repo}/actions/secrets/{name}",
                    json={"encrypted_value": enc, "key_id": pk["key_id"]},
                )
                status = "OK" if put.status_code in {201, 204} else f"FAIL HTTP {put.status_code}"
                print(f"{repo} | {name} -> {status}")
                if put.status_code not in {201, 204}:
                    ok = False
                    print(put.text[:200])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
