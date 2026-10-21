from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ProjectInvitation, ProjectMember, User
from .phones import normalize_phone
from .security import DUMMY_PASSWORD_HASH, verify_password


def authenticate_user(db: Session, phone: str, password: str) -> User | None:
    try:
        normalized_phone = normalize_phone(phone)
    except ValueError:
        verify_password(password[:128], DUMMY_PASSWORD_HASH)
        return None

    if len(password) > 128:
        verify_password(password[:128], DUMMY_PASSWORD_HASH)
        return None

    user = db.scalar(select(User).where(User.phone == normalized_phone))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def accept_pending_invitations(db: Session, user: User) -> None:
    invitations = list(
        db.scalars(
            select(ProjectInvitation).where(ProjectInvitation.phone == user.phone)
        ).all()
    )
    if not invitations:
        return

    existing_projects = set(
        db.scalars(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        ).all()
    )
    for invitation in invitations:
        if invitation.project_id not in existing_projects:
            db.add(
                ProjectMember(
                    project_id=invitation.project_id,
                    user_id=user.id,
                    role="member",
                )
            )
        db.delete(invitation)
    db.commit()
