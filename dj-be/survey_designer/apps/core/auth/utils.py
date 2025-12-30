import base64
import hashlib
import secrets


def generate_codes() -> (str, str):
    code_verifier = secrets.token_urlsafe(nbytes=64)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = (
        base64.urlsafe_b64encode(code_challenge).decode("utf-8").replace("=", "")
    )
    return code_challenge, code_verifier
