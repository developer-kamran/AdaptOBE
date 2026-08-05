from datetime import datetime, timedelta, timezone
from enum import Enum

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


class TokenType(str, Enum):
    access = "access"
    refresh = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


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
