import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import settings


class TokenType(str, Enum):
    access = "access"
    refresh = "refresh"


# Ambiguous glyphs (0/O, 1/l/I) are excluded so a password read off a screen
# or printed handout can't be mistyped.
_PASSWORD_LETTERS = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
_PASSWORD_DIGITS = "23456789"


def generate_password(length: int = 8) -> str:
    """Random password for accounts created in bulk, where no human picks one.

    Defaults to 8 characters, which is also the minimum `UserCreate.password`
    accepts. Guarantees at least one letter and one digit so the result is
    never all-numeric or all-alphabetic.
    """
    if length < 2:
        raise ValueError("password length must be at least 2")

    alphabet = _PASSWORD_LETTERS + _PASSWORD_DIGITS
    characters = [
        secrets.choice(_PASSWORD_LETTERS),
        secrets.choice(_PASSWORD_DIGITS),
        *(secrets.choice(alphabet) for _ in range(length - 2)),
    ]
    # Without shuffling, the letter and digit above would always land in
    # positions 0 and 1.
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def encrypt_password(password: str) -> str:
    """Reversible copy of a password so an authorized admin can view it again
    from the Edit page. Never used for authentication -- verify_password
    against the bcrypt hash is the only thing that decides a login."""
    return Fernet(settings.password_encryption_key.encode()).encrypt(password.encode()).decode()


def decrypt_password(token: str) -> str:
    return Fernet(settings.password_encryption_key.encode()).decrypt(token.encode()).decode()


def _create_token(subject: str, role: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str) -> str:
    return _create_token(
        subject, role, TokenType.access, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str, role: str) -> str:
    return _create_token(
        subject, role, TokenType.refresh, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
