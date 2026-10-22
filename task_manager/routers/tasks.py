from datetime import date
from typing import Literal

from fastapi import APIRouter
from sqlalchemy import case, select

from ..dependencies import CurrentUser, DbSession
from ..jalali import format_jalali
from ..models import BoardColumn, Project, ProjectMember, Task, task_assignees
from ..palette import PRIORITY_ORDER
from ..schemas import MyTaskRead

router = APIRouter(prefix="/api/my", tags=["my"])


def _priority_order():
    return case(PRIORITY_ORDER, value=Task.priority, else_=2)


@router.get("/tasks", response_model=list[MyTaskRead])
def my_tasks(
    db: DbSession,
    current_user: CurrentUser,
    scope: Literal["mine", "all"] = "mine",
    include_done: bool = True,
) -> list[MyTaskRead]:
    project_ids = list(
        db.scalars(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == current_user.id
            )
        ).all()
    )
    if not project_ids:
        return []

    statement = (
        select(Task, Project, BoardColumn.is_done)
        .join(Project, Task.project_id == Project.id)
        .join(BoardColumn, Task.column_id == BoardColumn.id)
        .where(Task.project_id.in_(project_ids))
    )
    if scope == "mine":
        statement = statement.join(
            task_assignees, Task.id == task_assignees.c.task_id
        ).where(task_assignees.c.user_id == current_user.id)
    if not include_done:
        statement = statement.where(BoardColumn.is_done.is_(False))

    statement = statement.order_by(
        _priority_order(),
        Task.due_date.is_(None),
        Task.due_date,
        Task.id,
    )

    today = date.today()
    result: list[MyTaskRead] = []
    for task, project, is_done in db.execute(statement).all():
        result.append(
            MyTaskRead(
                id=task.id,
                title=task.title,
                priority=task.priority,
                due_date=task.due_date,
                due_date_jalali=(
                    format_jalali(task.due_date) if task.due_date else None
                ),
                days_remaining=(
                    (task.due_date - today).days if task.due_date else None
                ),
                is_done=bool(is_done),
                project_id=project.id,
                project_name=project.name,
                project_color=project.color,
            )
        )
    return result
