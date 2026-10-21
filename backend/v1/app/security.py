from datetime import datetime, timedelta, timezone
from app.config import settings
import bcrypt
import jwt

#Security Constants and helper functions for password hashing and JWT token management
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# bcrypt only reads the first 72 bytes of a password (and bcrypt>=5 raises instead of truncating),
# so schemas reject anything longer -- see app/schemas/user.py
BCRYPT_MAX_BYTES = 72

def hash_password(plain_password: str) -> str:
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")
    # can never match a stored hash (those passwords are rejected at sign-up), and bcrypt would raise
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))

# checked against when a login names a user that doesn't exist (or hasn't registered), so that
# failed logins take the same time either way and response timing can't reveal valid usernames
DUMMY_PASSWORD_HASH = hash_password("timing-equalizer-not-a-real-password")

#This function creates a JWT access token with the provided data and an optional expiration time
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Decode a JWT access token and return the payload as a dictionary
def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
