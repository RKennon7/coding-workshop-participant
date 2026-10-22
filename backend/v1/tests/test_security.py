# pure unit tests for password hashing, JWTs and input validators -- no database needed
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.schemas.user import RegisterRequest, UserCreate
from app.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ---------- passwords ----------

def test_hash_is_salted_bcrypt_and_never_the_plain_password():
    first, second = hash_password("s3cret-pass"), hash_password("s3cret-pass")
    assert first.startswith("$2")
    assert "s3cret-pass" not in first
    assert first != second  # random salt per hash

def test_verify_password_accepts_only_the_right_password():
    hashed = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", hashed)
    assert not verify_password("s3cret-Pass", hashed)
    assert not verify_password("", hashed)

def test_verify_password_rejects_over_72_bytes_instead_of_truncating():
    # bcrypt only looks at the first 72 bytes, so without this check "<72 chars>anything" would match
    base = "a" * 72
    hashed = hash_password(base)
    assert verify_password(base, hashed)
    assert not verify_password(base + "extra", hashed)


# ---------- tokens ----------

def test_token_round_trip_carries_claims_and_expiry():
    token = create_access_token({"sub": "emp", "uid": 7, "role": "Employee"})
    payload = decode_access_token(token)
    assert payload["uid"] == 7 and payload["sub"] == "emp" and payload["role"] == "Employee"
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()

def test_expired_token_is_rejected():
    token = create_access_token({"uid": 1}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)

def test_token_signed_with_another_key_is_rejected():
    token = jwt.encode({"uid": 1, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, "attacker-controlled-key-of-a-realistic-length", algorithm=ALGORITHM)
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token)

def test_unsigned_alg_none_token_is_rejected():
    token = jwt.encode({"uid": 1}, key=None, algorithm="none")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)

def test_tampered_payload_is_rejected():
    header, _, signature = create_access_token({"uid": 1, "role": "Employee"}).split(".")
    forged_payload = jwt.utils.base64url_encode(b'{"uid":1,"role":"Facility Admin","exp":9999999999}').decode()
    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(f"{header}.{forged_payload}.{signature}")

def test_secret_key_is_loaded():
    assert SECRET_KEY  # an empty key would make every token trivially forgeable


# ---------- input validation ----------

@pytest.mark.parametrize("email", ["jane@acme.inc", "Jane.Doe@ACME.INC", "  jane@acme.inc  "])
def test_acme_emails_are_accepted_and_normalised(email):
    assert RegisterRequest(email=email, password="long-enough").email == email.strip().lower()

@pytest.mark.parametrize("email", [
    "jane@acme.com",
    "jane@gmail.com",
    "jane@evil.acme.inc",   # subdomain
    "jane@acme.inc.evil.com",
    "@acme.inc",
    "ja ne@acme.inc",
    "jane",
    "",
])
def test_non_acme_emails_are_rejected(email):
    with pytest.raises(ValidationError):
        RegisterRequest(email=email, password="long-enough")

@pytest.mark.parametrize("password", [
    "short",       # under 8 characters
    "a" * 73,      # over bcrypt's 72-byte limit
    "é" * 37,      # 37 characters but 74 bytes
])
def test_weak_or_unhashable_passwords_are_rejected(password):
    with pytest.raises(ValidationError):
        RegisterRequest(email="jane@acme.inc", password=password)

def test_password_at_the_72_byte_limit_is_allowed():
    assert RegisterRequest(email="jane@acme.inc", password="a" * 72)

def test_admin_created_user_defaults_to_least_privileged_role():
    assert UserCreate(username="newbie", email="newbie@acme.inc").role.value == "Employee"
