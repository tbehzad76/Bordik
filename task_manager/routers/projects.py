from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..dependencies import AppSettings, CurrentUser, DbSession
from ..models import (
    BoardColumn,
    Project,
    ProjectInvitation,
    ProjectMember,
    Task,
    User,
)
from ..notifications import notify_new_task
from ..permissions import (
    ensure_project_members,
    get_column,
    get_membership,
    get_task,
    load_board,
    move_task,
    next_position,
    project_member_ids,
    require_card_delete_permission,
    require_owner,
    require_project_access,
)
from ..schemas import (
    AssigneesUpdate,
    BoardRead,
    CardCreate,
    CardMove,
    CardRead,
    CardUpdate,
    ColumnCreate,
    ColumnRead,
    ColumnUpdate,
    InvitationRead,
    MemberInviteRequest,
    MemberInviteResult,
    MemberRead,
    ProjectCreate,
    ProjectSummary,
    ProjectUpdate,
    resolve_due_date,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])

DEFAULT_COLUMNS: tuple[tuple[str, bool], ...] = (
    ("برای انجام", False),
    ("در حال انجام", False),
    ("انجام‌شده", True),
)


def _summary(project: Project, role: str) -> ProjectSummary:
    done_column_ids = {column.id for column in project.columns if column.is_done}
    total = sum(len(column.cards) for column in project.columns)
    done = sum(
        1
        for column in project.columns
        for card in column.cards
        if card.column_id in done_column_ids
    )
    percent = round(done / total * 100) if total else 0
    return ProjectSummary(
        id=project.id,
        name=project.name,
        description=project.description,
        color=project.color,
        owner_id=project.owner_id,
        role=role,
        member_count=len(project.members),
        card_count=total,
        done_count=done,
        progress_percent=percent,
        created_at=project.created_at,
    )


def _board(db, project_id: int, user: User) -> BoardRead:
    project = load_board(db, project_id)
    membership = get_membership(db, project_id, user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )
    return BoardRead(
        id=project.id,
        name=project.name,
        description=project.description,
        color=project.color,
        owner_id=project.owner_id,
        role=membership.role,
        members=project.members,
        invitations=project.invitations,
        columns=project.columns,
    )


@router.get("", response_model=list[ProjectSummary])
def list_projects(db: DbSession, current_user: CurrentUser) -> list[ProjectSummary]:
    memberships = list(
        db.scalars(
            select(ProjectMember).where(ProjectMember.user_id == current_user.id)
        ).all()
    )
    if not memberships:
        return []

    project_ids = [membership.project_id for membership in memberships]
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.id.in_(project_ids))
            .options(
                selectinload(Project.members),
                selectinload(Project.columns).selectinload(BoardColumn.cards),
            )
            .order_by(Project.created_at.desc(), Project.id.desc())
        ).all()
    )
    roles = {membership.project_id: membership.role for membership in memberships}
    return [_summary(project, roles[project.id]) for project in projects]


@router.post("", response_model=BoardRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> BoardRead:
    project = Project(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        owner_id=current_user.id,
    )
    db.add(project)
    db.flush()

    db.add(
        ProjectMember(project_id=project.id, user_id=current_user.id, role="owner")
    )
    for position, (name, is_done) in enumerate(DEFAULT_COLUMNS):
        db.add(
            BoardColumn(
                project_id=project.id,
                name=name,
                position=position,
                is_done=is_done,
            )
        )
    db.commit()
    return _board(db, project.id, current_user)


@router.get("/{project_id}", response_model=BoardRead)
def get_board(
    project_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> BoardRead:
    return _board(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectSummary)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> ProjectSummary:
    project, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    changes = payload.model_dump(exclude_unset=True)
    for field_name, value in changes.items():
        setattr(project, field_name, value)
    db.commit()

    project = load_board(db, project_id)
    return _summary(project, membership.role)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    project, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)
    db.delete(project)
    db.commit()


@router.get("/{project_id}/members", response_model=list[MemberRead])
def list_members(
    project_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> list[ProjectMember]:
    require_project_access(db, project_id, current_user)
    return list(
        db.scalars(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .options(selectinload(ProjectMember.user))
            .order_by(ProjectMember.role.desc(), ProjectMember.id)
        ).all()
    )


@router.post(
    "/{project_id}/members",
    response_model=MemberInviteResult,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    project_id: int,
    payload: MemberInviteRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> MemberInviteResult:
    project, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    user = db.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        invitation = db.scalar(
            select(ProjectInvitation).where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.phone == payload.phone,
            )
        )
        if invitation is None:
            invitation = ProjectInvitation(
                project_id=project_id,
                phone=payload.phone,
                invited_by_id=current_user.id,
            )
            db.add(invitation)
            db.commit()
            db.refresh(invitation)
        return MemberInviteResult(status="invited", invitation=invitation)

    existing = get_membership(db, project_id, user.id)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already a member of the project",
        )

    member = ProjectMember(project_id=project_id, user_id=user.id, role="member")
    db.add(member)

    invitation = db.scalar(
        select(ProjectInvitation).where(
            ProjectInvitation.project_id == project_id,
            ProjectInvitation.phone == user.phone,
        )
    )
    if invitation is not None:
        db.delete(invitation)

    db.commit()
    db.refresh(member)
    member.user = user
    return MemberInviteResult(status="member", member=member)


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    project_id: int,
    user_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    project, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    if user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The project owner cannot be removed",
        )

    member = get_membership(db, project_id, user_id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    db.delete(member)
    db.commit()


@router.delete(
    "/{project_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_invitation(
    project_id: int,
    invitation_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    _, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    invitation = db.scalar(
        select(ProjectInvitation).where(
            ProjectInvitation.id == invitation_id,
            ProjectInvitation.project_id == project_id,
        )
    )
    if invitation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )
    db.delete(invitation)
    db.commit()


@router.post(
    "/{project_id}/columns",
    response_model=ColumnRead,
    status_code=status.HTTP_201_CREATED,
)
def create_column(
    project_id: int,
    payload: ColumnCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> BoardColumn:
    _, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    max_position = db.scalar(
        select(func.max(BoardColumn.position)).where(
            BoardColumn.project_id == project_id
        )
    )
    column = BoardColumn(
        project_id=project_id,
        name=payload.name,
        position=0 if max_position is None else int(max_position) + 1,
        is_done=payload.is_done,
    )
    db.add(column)
    db.commit()
    db.refresh(column)
    return column


@router.patch(
    "/{project_id}/columns/{column_id}",
    response_model=ColumnRead,
)
def update_column(
    project_id: int,
    column_id: int,
    payload: ColumnUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> BoardColumn:
    _, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    column = get_column(db, project_id, column_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(column, field_name, value)
    db.commit()
    db.refresh(column)
    return column


@router.delete(
    "/{project_id}/columns/{column_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_column(
    project_id: int,
    column_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    _, membership = require_project_access(db, project_id, current_user)
    require_owner(membership)

    column = get_column(db, project_id, column_id)
    card_count = db.scalar(
        select(func.count(Task.id)).where(Task.column_id == column_id)
    )
    if card_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Move or delete the cards in this column first",
        )

    column_count = db.scalar(
        select(func.count(BoardColumn.id)).where(
            BoardColumn.project_id == project_id
        )
    )
    if column_count is not None and column_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A project needs at least one column",
        )

    db.delete(column)
    db.commit()


@router.post(
    "/{project_id}/cards",
    response_model=CardRead,
    status_code=status.HTTP_201_CREATED,
)
def create_card(
    project_id: int,
    payload: CardCreate,
    db: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> Task:
    project, _ = require_project_access(db, project_id, current_user)

    if payload.column_id is None:
        column = db.scalar(
            select(BoardColumn)
            .where(BoardColumn.project_id == project_id)
            .order_by(BoardColumn.position)
            .limit(1)
        )
        if column is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The project has no columns",
            )
    else:
        column = get_column(db, project_id, payload.column_id)

    assignee_ids = payload.assignee_ids or [current_user.id]
    assignees = ensure_project_members(db, project_id, assignee_ids)
    card = Task(
        project_id=project.id,
        column_id=column.id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=resolve_due_date(payload.due_date, payload.due_in_days),
        position=next_position(db, column.id),
        created_by_id=current_user.id,
        assignees=assignees,
    )
    db.add(card)
    db.commit()
    notify_new_task(db, card, settings)
    db.refresh(card)
    return card


@router.get("/{project_id}/cards/{card_id}", response_model=CardRead)
def get_card(
    project_id: int,
    card_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    require_project_access(db, project_id, current_user)
    return get_task(db, project_id, card_id)


@router.patch("/{project_id}/cards/{card_id}", response_model=CardRead)
def update_card(
    project_id: int,
    card_id: int,
    payload: CardUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    require_project_access(db, project_id, current_user)
    card = get_task(db, project_id, card_id)

    changes = payload.model_dump(exclude_unset=True)
    assignee_ids = changes.pop("assignee_ids", None)
    due_in_days = changes.pop("due_in_days", None)
    due_date_provided = "due_date" in payload.model_fields_set
    changes.pop("due_date", None)

    for field_name, value in changes.items():
        setattr(card, field_name, value)

    if due_date_provided:
        card.due_date = payload.due_date
    elif due_in_days is not None:
        card.due_date = resolve_due_date(None, due_in_days)

    if assignee_ids is not None:
        if not assignee_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A card must have at least one assignee",
            )
        card.assignees = ensure_project_members(db, project_id, assignee_ids)

    db.commit()
    db.refresh(card)
    return card


@router.put("/{project_id}/cards/{card_id}/assignees", response_model=CardRead)
def set_card_assignees(
    project_id: int,
    card_id: int,
    payload: AssigneesUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    require_project_access(db, project_id, current_user)
    card = get_task(db, project_id, card_id)
    card.assignees = ensure_project_members(db, project_id, payload.user_ids)
    db.commit()
    db.refresh(card)
    return card


@router.post("/{project_id}/cards/{card_id}/move", response_model=CardRead)
def move_card(
    project_id: int,
    card_id: int,
    payload: CardMove,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    require_project_access(db, project_id, current_user)
    card = get_task(db, project_id, card_id)
    target_column = get_column(db, project_id, payload.column_id)
    move_task(db, card, target_column, payload.position)
    return card


@router.delete(
    "/{project_id}/cards/{card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_card(
    project_id: int,
    card_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
    _, membership = require_project_access(db, project_id, current_user)
    card = get_task(db, project_id, card_id)
    require_card_delete_permission(card, membership)
    db.delete(card)
    db.commit()
