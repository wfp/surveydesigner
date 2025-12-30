from core.auth.utils import generate_codes


def test_generate_codes():
    code_challenge, code_verifier = generate_codes()

    assert code_challenge and isinstance(code_challenge, str)
    assert code_verifier and isinstance(code_verifier, str)
