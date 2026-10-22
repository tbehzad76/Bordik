import pytest

from task_manager.database import Base, build_engine, build_session_factory
from task_manager.models import (
    BoardColumn,
    Project,
    ProjectMember,
    RubikaLink,
    Task,
    User,
)
from task_manager.phones import normalize_phone
from task_manager.rubika import extract_updates, handle_text
from task_manager.security import hash_password


@pytest.fixture()
def session(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'rubika.db'}")
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def make_user(db, phone="09120000001", name="کاربر تست"):
    user = User(
        phone=normalize_phone(phone),
        full_name=name,
        hashed_password=hash_password("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db, owner, name="Alpha"):
    project = Project(name=name, owner_id=owner.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=owner.id, role="owner"))
    for position, (column_name, is_done) in enumerate(
        (("برای انجام", False), ("در حال انجام", False), ("انجام‌شده", True))
    ):
        db.add(
            BoardColumn(
                project_id=project.id,
                name=column_name,
                position=position,
                is_done=is_done,
            )
        )
    db.commit()
    db.refresh(project)
    return project


def test_help_and_unlinked_commands(session):
    assert "دستورات بوردیک" in handle_text(session, "111", "/start")
    assert "اول حساب بوردیکت را وصل کن" in handle_text(session, "111", "/tasks")


def test_link_unknown_phone(session):
    reply = handle_text(session, "111", "/link 09129999999")

    assert "ثبت نشده" in reply
    assert session.query(RubikaLink).count() == 0


def test_link_and_list_tasks(session):
    user = make_user(session)
    project = make_project(session, user)
    column = session.query(BoardColumn).filter_by(project_id=project.id).first()
    session.add(
        Task(
            project_id=project.id,
            column_id=column.id,
            title="Test card",
            position=0,
            created_by_id=user.id,
        )
    )
    session.commit()

    assert "وصل شد" in handle_text(session, "111", "/link 09120000001")
    assert session.query(RubikaLink).one().user_id == user.id

    listing = handle_text(session, "111", "/tasks")
    assert "وظایف تو" in listing
    assert "Test card" in listing


def test_add_task(session):
    user = make_user(session)
    project = make_project(session, user, name="Alpha")
    handle_text(session, "111", "/link 09120000001")

    reply = handle_text(session, "111", "/add Alpha | کار جدید")

    assert "ساخته شد" in reply
    card = session.query(Task).filter_by(title="کار جدید").one()
    assert card.project_id == project.id
    assert card.created_by_id == user.id


def test_add_task_unknown_project(session):
    make_user(session)
    handle_text(session, "111", "/link 09120000001")

    assert "پیدا نشد" in handle_text(session, "111", "/add Nope | x")
    assert "قالب درست" in handle_text(session, "111", "/add بدون جداکننده")


def test_done_task(session):
    user = make_user(session)
    project = make_project(session, user)
    column = session.query(BoardColumn).filter_by(project_id=project.id).first()
    card = Task(
        project_id=project.id,
        column_id=column.id,
        title="Finish me",
        position=0,
        created_by_id=user.id,
    )
    session.add(card)
    session.commit()
    session.refresh(card)
    handle_text(session, "111", "/link 09120000001")

    reply = handle_text(session, "111", f"/done {card.id}")

    assert "انجام‌شده شد" in reply
    session.refresh(card)
    done_column = (
        session.query(BoardColumn)
        .filter_by(project_id=project.id, is_done=True)
        .one()
    )
    assert card.column_id == done_column.id
    assert "شماره کارت" in handle_text(session, "111", "/done abc")


def test_extract_updates_variants():
    payload = {
        "result": [
            {"update_id": 5, "message": {"chat_id": "42", "text": "/tasks"}},
            {"updateId": 6, "new_message": {"chatId": 43, "text": "/help"}},
            {"something": "else"},
        ]
    }

    updates = extract_updates(payload)

    assert updates == [
        {"update_id": 5, "chat_id": "42", "text": "/tasks"},
        {"update_id": 6, "chat_id": "43", "text": "/help"},
    ]
    assert extract_updates(None) == []
