import re

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import BASE_DIR

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


class Base(DeclarativeBase):
    pass


def resolve_database_url(database_url: str) -> str:
    """Make relative SQLite paths independent of the current working directory."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return database_url

    rest = database_url[len(prefix) :]
    if (
        rest.startswith(":memory:")
        or rest.startswith("/")
        or _WINDOWS_ABSOLUTE_PATH.match(rest)
    ):
        return database_url

    absolute_path = (BASE_DIR / rest).resolve()
    return prefix + str(absolute_path)


def build_engine(database_url: str) -> Engine:
    database_url = resolve_database_url(database_url)
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=not database_url.startswith("sqlite"),
    )

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
