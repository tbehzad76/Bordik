import pytest

from task_manager.config import Settings
from task_manager.database import Base, build_engine, build_session_factory
from task_manager.models import (
    BoardColumn,
    Project,
    ProjectMember,
    RubikaLink,
    Task,
    User,
)
from task_manager.notifications import build_new_task_message, notify_new_task
from task_manager.phones import normalize_phone
from task_manager.security import hash_password


class FakeClient:
    def __init__(self):
        self.sent = []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return {}


@pytest.fixture()
def session(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'notify.db'}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture()
def task_with_assignee(session):
    user = User(
        phone=normalize_phone("09120000001"),
        full_name="کاربر",
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    session.flush()

    project = Project(name="Alpha", owner_id=user.id, color="green")
    session.add(project)
    session.flush()
    session.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    column = BoardColumn(project_id=project.id, name="Todo", position=0)
    session.add(column)
    session.flush()

    task = Task(
        project_id=project.id,
        column_id=column.id,
        title="Huge task",
        priority="urgent",
        position=0,
        created_by_id=user.id,
        assignees=[user],
    )
    session.add(task)
    session.flush()
    session.add(RubikaLink(chat_id="555", user_id=user.id))
    session.commit()
    session.refresh(task)
    return task


def test_build_message_contains_details(task_with_assignee):
    message = build_new_task_message(task_with_assignee)

    assert "Huge task" in message
    assert "Alpha" in message
    assert "فوری" in message


def test_notify_disabled_is_noop(session, task_with_assignee):
    settings = Settings(jwt_secret_key="x" * 40, rubika_enabled=False)

    assert notify_new_task(session, task_with_assignee, settings) == []


def test_notify_sends_to_linked_assignees(session, task_with_assignee):
    settings = Settings(
        jwt_secret_key="x" * 40,
        rubika_enabled=True,
        rubika_bot_token="token",
    )
    client = FakeClient()

    sent = notify_new_task(session, task_with_assignee, settings, client=client)

    assert sent == ["555"]
    assert client.sent[0][0] == "555"
    assert "Huge task" in client.sent[0][1]
