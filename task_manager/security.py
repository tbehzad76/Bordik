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


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


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


def create_csrf_token(settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "type": "csrf",
        "nonce": secrets.token_urlsafe(32),
        "iat": now,
        "exp": now + timedelta(hours=1),
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
