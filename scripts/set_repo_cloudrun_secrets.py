"""Set PROVEPR_URL + PROVEPR_TRIGGER_SECRET on demo-shop (and optional repos)."""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from nacl import encoding, public

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPOS = ["hmik2003/provepr-demo-shop"]
DEFAULT_URL = "https://provepr-2f6eho3aiq-uc.a.run.app"


def encrypt_secret(public_key: str, secret_value: str) -> str:
    pk = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(sealed).decode("utf-8")


def main() -> int:
    load_dotenv(ROOT / ".env")
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        print("FAIL: GITHUB_TOKEN missing (needs Actions secrets: write)")
        return 1
    trigger = (os.getenv("PROVEPR_TRIGGER_SECRET") or "").strip()
    if not trigger:
        print("FAIL: PROVEPR_TRIGGER_SECRET missing in .env")
        return 1
    url = (os.getenv("PROVEPR_URL") or DEFAULT_URL).strip().rstrip("/")

    secrets = {
        "PROVEPR_URL": url,
        "PROVEPR_TRIGGER_SECRET": trigger,
    }
    repos = sys.argv[1:] or DEFAULT_REPOS

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ProvePR-setup",
    }
    ok = True
    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=60.0) as client:
        me = client.get("/user")
        if me.status_code != 200:
            print(f"FAIL: auth {me.status_code}")
            return 1
        print(f"Authenticated as {me.json().get('login')}")
        for repo in repos:
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
                status = "OK" if put.status_code in {201, 204} else f"FAIL {put.status_code}"
                print(f"{repo} | {name} -> {status}")
                if put.status_code not in {201, 204}:
                    ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
