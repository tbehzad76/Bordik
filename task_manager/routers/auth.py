from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..dependencies import AppSettings, CurrentUser, DbSession
from ..models import User
from ..schemas import LoginRequest, Token, UserRead, UserRegister
from ..security import create_access_token, hash_password
from ..services import accept_pending_invitations, authenticate_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect phone number or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserRegister, db: DbSession) -> User:
    phone = payload.phone

    if db.scalar(select(User.id).where(User.phone == phone)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists",
        )

    user = User(
        phone=phone,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number already exists",
        ) from None

    db.refresh(user)
    accept_pending_invitations(db, user)
    return user


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DbSession, settings: AppSettings) -> Token:
    user = authenticate_user(db, payload.phone, payload.password)
    if user is None:
        raise _invalid_credentials()

    return Token(access_token=create_access_token(user.id, settings))


@router.post("/token", response_model=Token, include_in_schema=False)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbSession,
    settings: AppSettings,
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        raise _invalid_credentials()

    return Token(access_token=create_access_token(user.id, settings))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: CurrentUser) -> User:
    return current_user
