import httpx
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from provepr.github_app import (
    build_app_jwt,
    create_installation_access_token,
    normalize_private_key,
)


def _test_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")


def test_normalize_private_key_escaped_newlines():
    raw = "-----BEGIN RSA PRIVATE KEY-----\\nABC\\n-----END RSA PRIVATE KEY-----"
    assert "\nABC\n" in normalize_private_key(raw)


def test_build_app_jwt_roundtrip():
    pem = _test_pem()
    token = build_app_jwt(app_id="12345", private_key_pem=pem, now=1_700_000_000)
    assert isinstance(token, str)
    assert token.count(".") == 2


@respx.mock
def test_create_installation_access_token():
    pem = _test_pem()
    respx.post("https://api.github.com/app/installations/99/access_tokens").mock(
        return_value=httpx.Response(201, json={"token": "ghs_test_token"})
    )
    token = create_installation_access_token(
        app_id="12345",
        private_key_pem=pem,
        installation_id="99",
    )
    assert token == "ghs_test_token"
