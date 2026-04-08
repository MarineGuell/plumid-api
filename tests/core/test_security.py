# api/tests/core/test_security.py
from core.security import hash_password, verify_password, create_access_token, decode_access_token
from jose import JWTError
import pytest


def test_hash_password():
    password = "MySuperSecretPassword#123"
    hashed = hash_password(password)
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_verify_password():
    password = "MySuperSecretPassword#123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_create_and_decode_access_token():
    data = {"sub": "123", "role": "admin"}
    token = create_access_token(data=data)
    assert isinstance(token, str)

    decoded = decode_access_token(token)
    assert decoded["sub"] == "123"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_decode_invalid_token():
    with pytest.raises(JWTError):
        decode_access_token("invalid.token.here")
