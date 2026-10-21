from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import Settings
from .models import User
from .security import InvalidAccessToken, decode_access_token

AUTH_COOKIE_NAME = "access_token"
CSRF_COOKIE_NAME = "csrf_token"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

UNAUTHORIZED_HEADERS = {"WWW-Authenticate": "Bearer"}


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[Session, None, None]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers=UNAUTHORIZED_HEADERS,
    )
    if not token:
        raise unauthorized

    try:
        user_id = decode_access_token(token, settings)
    except InvalidAccessToken:
        raise unauthorized from None

    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def get_optional_current_user(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> User | None:
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None
    try:
        user_id = decode_access_token(token, settings)
    except InvalidAccessToken:
        return None
    return db.get(User, user_id)


DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_current_user)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
