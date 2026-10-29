import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from . import models, ui  # noqa: F401
from .config import Settings, get_settings
from .database import Base, build_engine, build_session_factory
from .routers import auth, projects, tasks
from .rubika import run_polling

STATIC_DIR = Path(__file__).resolve().parent / "static"

access_logger = logging.getLogger("bordik.access")
if not access_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    access_logger.addHandler(handler)
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False


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
        if "priority" not in task_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE tasks ADD COLUMN priority "
                        "VARCHAR(10) NOT NULL DEFAULT 'normal'"
                    )
                )
        if "completed_at" not in task_columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE tasks ADD COLUMN completed_at DATETIME")
                )

    if "projects" in tables:
        project_columns = {
            column["name"] for column in inspector.get_columns("projects")
        }
        if "color" not in project_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE projects ADD COLUMN color "
                        "VARCHAR(20) NOT NULL DEFAULT 'blue'"
                    )
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
    app.include_router(tasks.router)
    app.include_router(ui.router)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if not path.startswith("/static") and path != "/health":
            access_logger.info(
                '%s %s -> %s scheme=%s host=%s ua="%s"',
                request.method,
                path,
                response.status_code,
                request.url.scheme,
                request.headers.get("host", "-"),
                (request.headers.get("user-agent") or "-")[:90],
            )
        return response

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    @app.exception_handler(ui.CsrfError)
    async def csrf_error_handler(request: Request, exc: ui.CsrfError) -> Response:
        return ui.csrf_error_response(
            request, request.app.state.settings, exc
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/diag", include_in_schema=False)
    def diag(request: Request) -> Response:
        """Open this from the phone to see how the request arrived."""
        settings: Settings = request.app.state.settings
        database = "ok"
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception as error:  # pragma: no cover - diagnostic only
            database = f"error: {type(error).__name__}"

        payload = {
            "status": "ok",
            "time_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "app": settings.app_name,
            "asset_version": ui.ASSET_VERSION,
            "scheme": request.url.scheme,
            "host": request.headers.get("host", "-"),
            "forwarded_proto": request.headers.get("x-forwarded-proto", "-"),
            "forwarded_for": request.headers.get("x-forwarded-for", "-"),
            "cookie_names": sorted(request.cookies.keys()),
            "secure_cookie_on_this_scheme": ui._cookie_secure(request),
            "session_days": settings.session_days,
            "cookie_secure_setting": settings.cookie_secure,
            "database": database,
            "user_agent": request.headers.get("user-agent", "-"),
        }
        return JSONResponse(payload)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest() -> Response:
        content = (STATIC_DIR / "manifest.webmanifest").read_text(encoding="utf-8")
        return Response(
            content=content,
            media_type="application/manifest+json",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/sw.js", include_in_schema=False)
    def service_worker() -> Response:
        content = (STATIC_DIR / "sw.js").read_text(encoding="utf-8")
        return Response(
            content=content,
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-cache",
                "Service-Worker-Allowed": "/",
            },
        )

    return app
