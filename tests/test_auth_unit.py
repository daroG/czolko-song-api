from app.auth import verify_code


def test_verify_code_true():
    assert verify_code("secret", "secret") is True


def test_verify_code_false():
    assert verify_code("secret", "nope") is False
