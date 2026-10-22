import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from . import models, ui  # noqa: F401
from .config import Settings, get_settings
from .database import Base, build_engine, build_session_factory
from .routers import auth, projects
from .rubika import run_polling

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _prepare_schema(engine, settings: Settings) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "users" in tables:
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "phone" not in columns:
            raise RuntimeError(
                "The database schema is outdated (users.phone is missing). "
                "For development delete the SQLite file and restart. "
                "For production run 'alembic upgrade head'."
            )

    if not settings.auto_create_tables or engine.dialect.name != "sqlite":
        return

    if "tasks" in tables:
        task_columns = {column["name"] for column in inspector.get_columns("tasks")}
        if "due_date" not in task_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE tasks ADD COLUMN due_date DATE")
                )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = build_engine(settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if settings.auto_create_tables:
            Base.metadata.create_all(bind=engine)
        _prepare_schema(engine, settings)

        rubika_task = None
        if settings.rubika_enabled and settings.rubika_bot_token:
            rubika_task = asyncio.create_task(
                run_polling(session_factory, settings)
            )
        try:
            yield
        finally:
            if rubika_task is not None:
                rubika_task.cancel()
                with suppress(asyncio.CancelledError):
                    await rubika_task
            engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(ui.router)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
