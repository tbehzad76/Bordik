import asyncio
import json
import logging
import urllib.error
import urllib.request
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .jalali import format_jalali
from .models import BoardColumn, ProjectMember, RubikaLink, Task, User
from .permissions import move_task, next_position
from .phones import normalize_phone

logger = logging.getLogger(__name__)

HELP_TEXT = (
    "دستورات بوردیک:\n"
    "/link 09121234567  اتصال این چت به حساب بوردیک\n"
    "/tasks  لیست وظایف من\n"
    "/add نام پروژه | عنوان کارت  افزودن کارت\n"
    "/done 12  انجام‌شده کردن کارت شماره ۱۲"
)


class RubikaError(Exception):
    pass


class RubikaClient:
    """Minimal client for the Rubika bot HTTP API.

    Method names are configurable because Rubika's API may differ between
    versions; defaults follow the Telegram-like naming used by Rubika.
    """

    def __init__(self, settings: Settings):
        self.base_url = settings.rubika_api_base.rstrip("/")
        self.token = settings.rubika_bot_token
        self.send_method = settings.rubika_send_method
        self.updates_method = settings.rubika_updates_method
        self.timeout = 20

    def _url(self, method: str) -> str:
        return f"{self.base_url}/{self.token}/{method}"

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise RubikaError("RUBIKA_BOT_TOKEN is not set")

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self._url(method),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.URLError as exc:
            raise RubikaError(str(exc)) from exc

        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            return {"raw": body.decode("utf-8", "replace")}

    def send_message(self, chat_id: str, text: str) -> dict[str, Any]:
        return self._post(self.send_method, {"chat_id": chat_id, "text": text})

    def get_updates(self, offset: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if offset is not None:
            payload["offset"] = offset
        return self._post(self.updates_method, payload)


def extract_updates(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    items = payload.get("result")
    if items is None:
        items = payload.get("updates")
    if items is None:
        items = payload.get("data") or []
    if isinstance(items, dict):
        items = items.get("updates", [])
    if not isinstance(items, list):
        return []

    updates: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        message = (
            item.get("message")
            or item.get("new_message")
            or item.get("newMessage")
            or {}
        )
        chat_id = (
            message.get("chat_id")
            or message.get("chatId")
            or item.get("chat_id")
            or item.get("chatId")
        )
        text = message.get("text") or item.get("text") or ""
        if chat_id is None:
            continue
        updates.append(
            {
                "update_id": item.get("update_id") or item.get("updateId"),
                "chat_id": str(chat_id),
                "text": str(text),
            }
        )
    return updates


def _link_for(db: Session, chat_id: str) -> RubikaLink | None:
    return db.scalar(select(RubikaLink).where(RubikaLink.chat_id == str(chat_id)))


def _user_project_ids(db: Session, user_id: int) -> list[int]:
    return list(
        db.scalars(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        ).all()
    )


def handle_text(db: Session, chat_id: str | int, text: str) -> str:
    text = (text or "").strip()
    command, _, argument = text.partition(" ")
    command = command.lower()
    argument = argument.strip()

    if command in ("/start", "/help"):
        return HELP_TEXT
    if command == "/link":
        return _link_account(db, chat_id, argument)

    link = _link_for(db, chat_id)
    if link is None:
        return "اول حساب بوردیکت را وصل کن: /link شماره‌همراه"
    user = db.get(User, link.user_id)
    if user is None:
        return "حساب متصل پیدا نشد؛ دوباره /link بزن."

    if command == "/tasks":
        return _list_tasks(db, user)
    if command == "/add":
        return _add_task(db, user, argument)
    if command == "/done":
        return _done_task(db, user, argument)
    return HELP_TEXT


def _link_account(db: Session, chat_id: str | int, argument: str) -> str:
    if not argument:
        return "شماره همراه را کنار دستور بنویس: /link 09121234567"
    try:
        phone = normalize_phone(argument)
    except ValueError:
        return "شماره همراه معتبر نیست."

    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        return "حسابی با این شماره ثبت نشده. اول در سایت بوردیک ثبت‌نام کن."

    link = _link_for(db, chat_id)
    if link is None:
        db.add(RubikaLink(chat_id=str(chat_id), user_id=user.id))
    else:
        link.user_id = user.id
    db.commit()
    return f"وصل شد، {user.full_name}! با /tasks لیست وظایفت را ببین."


def _list_tasks(db: Session, user: User) -> str:
    project_ids = _user_project_ids(db, user.id)
    if not project_ids:
        return "هنوز عضو هیچ پروژه‌ای نیستی."

    tasks = list(
        db.scalars(
            select(Task)
            .where(Task.project_id.in_(project_ids))
            .options(selectinload(Task.project), selectinload(Task.column))
            .order_by(Task.due_date.is_(None), Task.due_date, Task.id)
            .limit(20)
        ).all()
    )
    if not tasks:
        return "وظیفه‌ای نداری."

    lines = ["وظایف تو:"]
    for task in tasks:
        status = "[x]" if task.column and task.column.is_done else "[ ]"
        due = f" | سررسید {format_jalali(task.due_date)}" if task.due_date else ""
        project_name = task.project.name if task.project else "-"
        lines.append(f"{status} #{task.id} [{project_name}] {task.title}{due}")
    return "\n".join(lines)


def _add_task(db: Session, user: User, argument: str) -> str:
    if "|" not in argument:
        return "قالب درست: /add نام پروژه | عنوان کارت"
    project_name, _, title = argument.partition("|")
    project_name = project_name.strip()
    title = title.strip()
    if not project_name or not title:
        return "نام پروژه و عنوان کارت را کامل بنویس."

    memberships = list(
        db.scalars(
            select(ProjectMember)
            .where(ProjectMember.user_id == user.id)
            .options(selectinload(ProjectMember.project))
        ).all()
    )
    project = next(
        (
            membership.project
            for membership in memberships
            if membership.project
            and membership.project.name.strip().lower() == project_name.lower()
        ),
        None,
    )
    if project is None:
        return f"پروژه‌ای با نام «{project_name}» پیدا نشد."

    column = db.scalar(
        select(BoardColumn)
        .where(BoardColumn.project_id == project.id)
        .order_by(BoardColumn.position)
        .limit(1)
    )
    if column is None:
        return "این پروژه ستون ندارد."

    task = Task(
        project_id=project.id,
        column_id=column.id,
        title=title,
        position=next_position(db, column.id),
        created_by_id=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return f"کارت #{task.id} در «{project.name}» ساخته شد."


def _done_task(db: Session, user: User, argument: str) -> str:
    if not argument.strip().isdigit():
        return "شماره کارت را بده: /done 12"

    project_ids = _user_project_ids(db, user.id)
    if not project_ids:
        return "هنوز عضو هیچ پروژه‌ای نیستی."

    task = db.scalar(
        select(Task)
        .where(Task.id == int(argument.strip()), Task.project_id.in_(project_ids))
        .options(selectinload(Task.column))
    )
    if task is None:
        return "کارت با این شماره پیدا نشد."

    done_column = db.scalar(
        select(BoardColumn)
        .where(
            BoardColumn.project_id == task.project_id,
            BoardColumn.is_done.is_(True),
        )
        .order_by(BoardColumn.position)
        .limit(1)
    )
    if done_column is None:
        return "برای این پروژه ستون «انجام‌شده» تعریف نشده."

    if task.column_id != done_column.id:
        move_task(db, task, done_column, 0)
    return f"کارت #{task.id} انجام‌شده شد."


def _handle_in_session(session_factory, chat_id: str, text: str) -> str:
    db = session_factory()
    try:
        return handle_text(db, chat_id, text)
    finally:
        db.close()


async def run_polling(session_factory, settings: Settings) -> None:
    client = RubikaClient(settings)
    offset: int | None = None

    while True:
        try:
            payload = await asyncio.to_thread(client.get_updates, offset)
            for update in extract_updates(payload):
                if update["update_id"] is not None:
                    try:
                        offset = int(update["update_id"]) + 1
                    except (TypeError, ValueError):
                        offset = offset
                reply = await asyncio.to_thread(
                    _handle_in_session,
                    session_factory,
                    update["chat_id"],
                    update["text"],
                )
                if reply:
                    await asyncio.to_thread(
                        client.send_message, update["chat_id"], reply
                    )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the polling loop alive
            logger.exception("Rubika polling failed")
        await asyncio.sleep(settings.rubika_poll_interval_seconds)
