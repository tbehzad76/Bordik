import secrets
from datetime import UTC, datetime, timedelta

import jwt
from jwt import InvalidTokenError as JWTError
from pwdlib import PasswordHash

from .config import Settings

password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("timing-attack-mitigation-placeholder")


class InvalidAccessToken(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except Exception:
        return False


def create_access_token(
    user_id: int,
    settings: Settings,
    expires_minutes: int | None = None,
) -> str:
    lifetime = (
        expires_minutes
        if expires_minutes is not None
        else settings.access_token_expire_minutes
    )
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=lifetime),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def token_remaining_seconds(token: str, settings: Settings) -> float | None:
    """Seconds until the token expires, without validating the signature age."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        expires_at = payload.get("exp")
        if expires_at is None:
            return None
        return (
            datetime.fromtimestamp(float(expires_at), UTC) - datetime.now(UTC)
        ).total_seconds()
    except (JWTError, KeyError, TypeError, ValueError):
        return None


def decode_access_token(token: str, settings: Settings) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
        if payload.get("type") != "access":
            raise InvalidAccessToken("unexpected token type")
        user_id = int(payload["sub"])
        if user_id <= 0:
            raise InvalidAccessToken("invalid token subject")
        return user_id
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidAccessToken("invalid or expired token") from exc


def create_csrf_token(
    settings: Settings, expires_minutes: int | None = None
) -> str:
    lifetime = (
        expires_minutes
        if expires_minutes is not None
        else settings.session_days * 24 * 60
    )
    now = datetime.now(UTC)
    payload = {
        "type": "csrf",
        "nonce": secrets.token_urlsafe(32),
        "iat": now,
        "exp": now + timedelta(minutes=lifetime),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def is_valid_csrf_token(token: str, settings: Settings) -> bool:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat"]},
        )
        return payload.get("type") == "csrf" and bool(payload.get("nonce"))
    except JWTError:
        return False
