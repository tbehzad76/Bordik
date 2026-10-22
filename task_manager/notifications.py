import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings
from .jalali import format_jalali
from .models import Notification, RubikaLink, Task, User
from .palette import PRIORITY_LABELS

logger = logging.getLogger(__name__)


def build_new_task_message(task: Task) -> str:
    lines = [f"وظیفه جدید: {task.title}"]
    if task.project is not None:
        lines.append(f"پروژه: {task.project.name}")
    if task.due_date is not None:
        lines.append(f"سررسید: {format_jalali(task.due_date)}")
    lines.append(f"اولویت: {PRIORITY_LABELS.get(task.priority, 'معمولی')}")
    return "\n".join(lines)


def create_task_notifications(db: Session, task: Task) -> list[Notification]:
    """Store an in-app notification for every assignee of the task."""
    created: list[Notification] = []
    project_name = task.project.name if task.project is not None else ""
    body = f"پروژه: {project_name} · اولویت: {PRIORITY_LABELS.get(task.priority, 'معمولی')}"
    if task.due_date is not None:
        body += f" · سررسید: {format_jalali(task.due_date)}"

    for assignee in task.assignees:
        notification = Notification(
            user_id=assignee.id,
            title=f"وظیفه جدید: {task.title}",
            body=body,
            url=f"/projects/{task.project_id}/cards/{task.id}",
        )
        db.add(notification)
        created.append(notification)
    if created:
        db.commit()
    return created


def notify_new_task(
    db: Session,
    task: Task,
    settings: Settings,
    client=None,
) -> list[str]:
    """Store in-app notifications and push them to linked Rubika accounts.

    Returns the list of Rubika chat ids that were messaged. Storage happens even
    when the Rubika bot is disabled; the browser UI polls those rows.
    """
    create_task_notifications(db, task)

    assignee_ids = [assignee.id for assignee in task.assignees]
    if not assignee_ids:
        return []

    if client is None:
        if not settings.rubika_enabled or not settings.rubika_bot_token:
            return []
        from .rubika import RubikaClient

        client = RubikaClient(settings)

    links = list(
        db.scalars(
            select(RubikaLink).where(RubikaLink.user_id.in_(assignee_ids))
        ).all()
    )
    if not links:
        return []

    text = build_new_task_message(task)
    sent: list[str] = []
    for link in links:
        try:
            client.send_message(link.chat_id, text)
            sent.append(link.chat_id)
        except Exception:  # noqa: BLE001 - one failed chat must not break others
            logger.exception("Rubika notification failed for chat %s", link.chat_id)
    return sent
