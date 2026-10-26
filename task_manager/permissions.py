from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import BoardColumn, Project, ProjectMember, Task, User

BOARD_LOAD_OPTIONS = (
    selectinload(Project.members).selectinload(ProjectMember.user),
    selectinload(Project.invitations),
    selectinload(Project.columns)
    .selectinload(BoardColumn.cards)
    .selectinload(Task.assignees),
    selectinload(Project.columns)
    .selectinload(BoardColumn.cards)
    .selectinload(Task.created_by),
)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Project not found",
    )


def get_membership(
    db: Session, project_id: int, user_id: int
) -> ProjectMember | None:
    return db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )


def require_project_access(
    db: Session, project_id: int, user: User
) -> tuple[Project, ProjectMember]:
    project = db.get(Project, project_id)
    membership = get_membership(db, project_id, user.id)
    if project is None or membership is None:
        raise _not_found()
    return project, membership


def require_owner(membership: ProjectMember) -> None:
    if membership.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project owner can do this",
        )


def can_delete_card(card: Task, membership: ProjectMember) -> bool:
    if card.created_by_id is not None:
        return card.created_by_id == membership.user_id
    return membership.role == "owner"


def require_card_delete_permission(card: Task, membership: ProjectMember) -> None:
    if not can_delete_card(card, membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the card creator can delete this card",
        )


def load_board(db: Session, project_id: int) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(*BOARD_LOAD_OPTIONS)
    )
    if project is None:
        raise _not_found()
    return project


def get_column(db: Session, project_id: int, column_id: int) -> BoardColumn:
    column = db.scalar(
        select(BoardColumn).where(
            BoardColumn.id == column_id,
            BoardColumn.project_id == project_id,
        )
    )
    if column is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Column not found",
        )
    return column


def get_task(db: Session, project_id: int, task_id: int) -> Task:
    task = db.scalar(
        select(Task)
        .where(Task.id == task_id, Task.project_id == project_id)
        .options(selectinload(Task.assignees), selectinload(Task.created_by))
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Card not found",
        )
    return task


def project_member_ids(db: Session, project_id: int) -> set[int]:
    return set(
        db.scalars(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_id
            )
        ).all()
    )


def ensure_project_members(
    db: Session, project_id: int, user_ids: list[int]
) -> list[User]:
    unique_ids = list(dict.fromkeys(user_ids))
    if not unique_ids:
        return []

    members = set(project_member_ids(db, project_id))
    unknown = [user_id for user_id in unique_ids if user_id not in members]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All assignees must be members of the project",
        )

    users = list(
        db.scalars(select(User).where(User.id.in_(unique_ids))).all()
    )
    by_id = {user.id: user for user in users}
    return [by_id[user_id] for user_id in unique_ids if user_id in by_id]


def next_position(db: Session, column_id: int) -> int:
    current = db.scalar(
        select(Task.position)
        .where(Task.column_id == column_id)
        .order_by(Task.position.desc())
        .limit(1)
    )
    return 0 if current is None else int(current) + 1


def move_task(
    db: Session,
    task: Task,
    target_column: BoardColumn,
    target_index: int,
) -> None:
    source_column_id = task.column_id

    source_tasks = list(
        db.scalars(
            select(Task)
            .where(Task.column_id == source_column_id, Task.id != task.id)
            .order_by(Task.position, Task.id)
        ).all()
    )

    if source_column_id == target_column.id:
        index = max(0, min(target_index, len(source_tasks)))
        ordered = source_tasks
        ordered.insert(index, task)
        for position, item in enumerate(ordered):
            item.position = position
        db.commit()
        db.refresh(task)
        return

    target_tasks = list(
        db.scalars(
            select(Task)
            .where(Task.column_id == target_column.id)
            .order_by(Task.position, Task.id)
        ).all()
    )
    index = max(0, min(target_index, len(target_tasks)))
    target_tasks.insert(index, task)
    task.column_id = target_column.id

    for position, item in enumerate(source_tasks):
        item.position = position
    for position, item in enumerate(target_tasks):
        item.position = position

    db.commit()
    db.refresh(task)
