import secrets
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError

from .config import Settings
from .dependencies import (
    AUTH_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    AppSettings,
    DbSession,
    OptionalUser,
)
from .jalali import format_jalali, format_jalali_datetime, parse_jalali
from .models import (
    BoardColumn,
    Notification,
    Project,
    ProjectInvitation,
    ProjectMember,
    Task,
    User,
    task_assignees,
    utc_now,
)
from .notifications import notify_new_task
from .palette import (
    PRIORITY_CLASSES,
    PRIORITY_LABELS,
    PRIORITY_ORDER,
    PROJECT_COLORS,
    PROJECT_COLOR_LABELS,
    is_valid_project_color,
)
from .permissions import (
    can_delete_card,
    ensure_project_members,
    get_column,
    get_membership,
    get_task,
    load_board,
    move_task,
    next_position,
)
from .phones import normalize_phone
from .schemas import (
    CardMove,
    ColumnCreate,
    ColumnUpdate,
    ProjectCreate,
    UserRegister,
    resolve_due_date,
)
from .security import (
    create_access_token,
    create_csrf_token,
    hash_password,
    is_valid_csrf_token,
    token_remaining_seconds,
)
from .services import accept_pending_invitations, authenticate_user

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["jdate"] = format_jalali
templates.env.filters["jdatetime"] = format_jalali_datetime
templates.env.filters["priority_label"] = lambda value: PRIORITY_LABELS.get(
    value, value
)
templates.env.globals["PRIORITY_LABELS"] = PRIORITY_LABELS
templates.env.globals["PRIORITY_CLASSES"] = PRIORITY_CLASSES
templates.env.globals["PROJECT_COLORS"] = PROJECT_COLORS
templates.env.globals["PROJECT_COLOR_LABELS"] = PROJECT_COLOR_LABELS

router = APIRouter(include_in_schema=False)

DEFAULT_COLUMNS = (
    ("برای انجام", False),
    ("در حال انجام", False),
    ("انجام‌شده", True),
)

ASSET_VERSION = "28"

FormPhone = Annotated[str, Form(min_length=1, max_length=30)]
FormPassword = Annotated[str, Form(min_length=1, max_length=128)]
FormName = Annotated[str, Form(min_length=1, max_length=100)]
ProjectName = Annotated[str, Form(min_length=1, max_length=120)]
ProjectDescription = Annotated[str, Form(max_length=2000)]
ColumnName = Annotated[str, Form(min_length=1, max_length=60)]
CardTitle = Annotated[str, Form(min_length=1, max_length=200)]
CardDescription = Annotated[str, Form(max_length=5000)]
CsrfToken = Annotated[str, Form(min_length=1, max_length=512)]


def _parse_due_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    try:
        return parse_jalali(value)
    except ValueError:
        return None


def _valid_csrf(request: Request, settings: Settings, supplied: str | None) -> bool:
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    if (
        not supplied
        or not cookie_token
        or not secrets.compare_digest(cookie_token, supplied)
    ):
        return False
    return is_valid_csrf_token(cookie_token, settings)


def require_csrf(
    request: Request,
    settings: AppSettings,
    csrf_token: CsrfToken,
) -> None:
    if not _valid_csrf(request, settings, csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


def require_csrf_header(
    request: Request,
    settings: AppSettings,
    x_csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    if not _valid_csrf(request, settings, x_csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid CSRF token",
        )


CsrfProtected = Annotated[None, Depends(require_csrf)]
CsrfHeaderProtected = Annotated[None, Depends(require_csrf_header)]


def _auth_cookie_lifetime_minutes(settings: Settings, remember: bool) -> int:
    if remember:
        return settings.session_days * 24 * 60
    return settings.access_token_expire_minutes


def _set_auth_cookie(
    response: Response,
    user_id: int,
    settings: Settings,
    remember: bool = True,
) -> None:
    lifetime_minutes = _auth_cookie_lifetime_minutes(settings, remember)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=create_access_token(
            user_id, settings, expires_minutes=lifetime_minutes
        ),
        max_age=lifetime_minutes * 60 if remember else None,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def _refresh_auth_cookie(
    request: Request,
    response: Response,
    user: User | None,
    settings: Settings,
) -> None:
    """Slide the session forward so a phone stays signed in without re-login."""
    if user is None:
        return
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return
    remaining = token_remaining_seconds(token, settings)
    if remaining is None:
        return
    if remaining <= settings.session_days * 86400 / 2:
        _set_auth_cookie(response, user.id, settings)


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(url=path, status_code=status.HTTP_303_SEE_OTHER)


def _render_page(
    request: Request,
    template_name: str,
    settings: Settings,
    user: User | None = None,
    **context,
) -> HTMLResponse:
    csrf_token = request.cookies.get(CSRF_COOKIE_NAME)
    issue_csrf_cookie = not csrf_token or not is_valid_csrf_token(csrf_token, settings)
    if issue_csrf_cookie:
        csrf_token = create_csrf_token(settings)

    response = templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "user": user,
            "csrf_token": csrf_token,
            "current_year": datetime.now(UTC).year,
            "asset_version": ASSET_VERSION,
            **context,
        },
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "font-src 'self'; script-src 'self'; connect-src 'self'; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"

    if issue_csrf_cookie:
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_token,
            max_age=settings.session_days * 86400,
            httponly=True,
            samesite="lax",
            secure=settings.cookie_secure,
            path="/",
        )
    _refresh_auth_cookie(request, response, user, settings)
    return response


def _board_for(db, project_id: int, user: User):
    project = load_board(db, project_id)
    membership = get_membership(db, project_id, user.id)
    return project, membership


def _board_context(project: Project, membership: ProjectMember) -> dict:
    done_column_ids = {column.id for column in project.columns if column.is_done}
    total = sum(len(column.cards) for column in project.columns)
    done = sum(
        1
        for column in project.columns
        for card in column.cards
        if card.column_id in done_column_ids
    )
    return {
        "project": project,
        "membership": membership,
        "members": project.members,
        "invitations": project.invitations,
        "columns": project.columns,
        "is_owner": membership.role == "owner",
        "today": date.today(),
        "progress": {
            "total": total,
            "done": done,
            "percent": round(done / total * 100) if total else 0,
        },
    }


@router.get("/", response_class=HTMLResponse)
def home(user: OptionalUser) -> Response:
    if user is None:
        return _redirect("/login")
    return _redirect("/projects")


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    settings: AppSettings,
    user: OptionalUser,
) -> Response:
    if user is not None:
        return _redirect("/projects")
    return _render_page(request, "login.html", settings, phone="")


@router.post("/login")
def login_submit(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    phone: FormPhone,
    password: FormPassword,
    _csrf: CsrfProtected,
    remember: Annotated[str | None, Form()] = None,
) -> Response:
    user = authenticate_user(db, phone, password)
    if user is None:
        return _render_page(
            request,
            "login.html",
            settings,
            phone=phone,
            error="شماره همراه یا رمز عبور نادرست است.",
        )

    response = _redirect("/projects")
    _set_auth_cookie(response, user.id, settings, remember=bool(remember))
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    settings: AppSettings,
    user: OptionalUser,
) -> Response:
    if user is not None:
        return _redirect("/projects")
    return _render_page(
        request, "register.html", settings, full_name="", phone=""
    )


@router.post("/register")
def register_submit(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    full_name: FormName,
    phone: FormPhone,
    password: FormPassword,
    password_confirm: Annotated[str, Form(min_length=1, max_length=128)],
    _csrf: CsrfProtected,
) -> Response:
    error = None
    normalized_phone = None
    if password != password_confirm:
        error = "رمز عبور و تکرار آن یکسان نیستند."
    elif not password.strip():
        error = "رمز عبور نمی‌تواند خالی باشد."
    elif not 8 <= len(password) <= 128:
        error = "رمز عبور باید بین ۸ تا ۱۲۸ کاراکتر باشد."
    else:
        try:
            validated = UserRegister(
                full_name=full_name,
                phone=phone,
                password=password,
            )
            normalized_phone = validated.phone
        except ValueError:
            error = "نام یا شماره همراه واردشده معتبر نیست."

    if error is None and normalized_phone is not None:
        if (
            db.scalar(select(User.id).where(User.phone == normalized_phone))
            is not None
        ):
            error = "حسابی با این شماره همراه از قبل وجود دارد."

    if error is not None or normalized_phone is None:
        return _render_page(
            request,
            "register.html",
            settings,
            full_name=full_name,
            phone=phone,
            error=error or "اطلاعات واردشده معتبر نیست.",
        )

    user = User(
        phone=normalized_phone,
        full_name=full_name.strip(),
        hashed_password=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _render_page(
            request,
            "register.html",
            settings,
            full_name=full_name,
            phone=phone,
            error="حسابی با این شماره همراه از قبل وجود دارد.",
        )

    db.refresh(user)
    accept_pending_invitations(db, user)

    response = _redirect("/projects")
    _set_auth_cookie(response, user.id, settings)
    return response


@router.post("/projects/{project_id}/delete")
def delete_project_form(
    project_id: int,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    project, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")
    if membership.role == "owner":
        db.delete(project)
        db.commit()
    return _redirect("/projects")


@router.get("/my-tasks", response_class=HTMLResponse)
def my_tasks_page(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    user: OptionalUser,
    scope: str = "mine",
    include_done: str = "0",
) -> Response:
    if user is None:
        return _redirect("/login")

    project_ids = list(
        db.scalars(
            select(ProjectMember.project_id).where(
                ProjectMember.user_id == user.id
            )
        ).all()
    )
    rows = []
    if project_ids:
        statement = (
            select(Task, Project, BoardColumn.is_done)
            .join(Project, Task.project_id == Project.id)
            .join(BoardColumn, Task.column_id == BoardColumn.id)
            .where(Task.project_id.in_(project_ids))
        )
        if scope != "all":
            statement = statement.join(
                task_assignees, Task.id == task_assignees.c.task_id
            ).where(task_assignees.c.user_id == user.id)
        if include_done != "1":
            statement = statement.where(BoardColumn.is_done.is_(False))
        statement = statement.order_by(
            case(PRIORITY_ORDER, value=Task.priority, else_=2),
            Task.due_date.is_(None),
            Task.due_date,
            Task.id,
        )
        for task, project, is_done in db.execute(statement).all():
            rows.append(
                {
                    "task": task,
                    "project": project,
                    "is_done": bool(is_done),
                    "days": (
                        None
                        if is_done or task.completed_at is not None
                        else (
                            (task.due_date - date.today()).days
                            if task.due_date
                            else None
                        )
                    ),
                }
            )

    return _render_page(
        request,
        "my_tasks.html",
        settings,
        user=user,
        rows=rows,
        scope=scope,
        include_done=include_done,
    )


@router.get("/ui/notifications/feed", include_in_schema=False)
def notifications_feed(db: DbSession, user: OptionalUser) -> Response:
    if user is None:
        return JSONResponse({"items": [], "unread": 0}, status_code=401)

    items = list(
        db.scalars(
            select(Notification)
            .where(Notification.user_id == user.id)
            .order_by(Notification.id.desc())
            .limit(20)
        ).all()
    )
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
    ) or 0
    return JSONResponse(
        {
            "unread": unread,
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "body": item.body,
                    "url": item.url,
                    "is_read": item.is_read,
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ],
        }
    )


@router.post("/ui/notifications/read", include_in_schema=False)
async def notifications_read(
    request: Request,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfHeaderProtected,
) -> Response:
    if user is None:
        return JSONResponse({"ok": False}, status_code=401)

    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001 - empty body means "mark everything"
        payload = {}

    statement = select(Notification).where(
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    )
    ids = payload.get("ids") if isinstance(payload, dict) else None
    if isinstance(ids, list) and ids:
        numeric_ids = [int(value) for value in ids if str(value).isdigit()]
        if numeric_ids:
            statement = statement.where(Notification.id.in_(numeric_ids))

    for notification in db.scalars(statement).all():
        notification.is_read = True
    db.commit()
    return JSONResponse({"ok": True})


@router.post("/logout")
def logout(settings: AppSettings, _csrf: CsrfProtected) -> Response:
    response = _redirect("/login")
    response.delete_cookie(
        AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response


@router.get("/projects", response_class=HTMLResponse)
def projects_page(
    request: Request,
    db: DbSession,
    settings: AppSettings,
    user: OptionalUser,
) -> Response:
    if user is None:
        return _redirect("/login")

    memberships = list(
        db.scalars(
            select(ProjectMember).where(ProjectMember.user_id == user.id)
        ).all()
    )
    project_rows = []
    if memberships:
        roles = {member.project_id: member.role for member in memberships}
        projects = list(
            db.scalars(
                select(Project)
                .where(Project.id.in_(list(roles)))
                .order_by(Project.created_at.desc(), Project.id.desc())
            ).all()
        )
        project_rows = []
        for project in projects:
            total = db.scalar(
                select(func.count(Task.id)).where(Task.project_id == project.id)
            ) or 0
            done = db.scalar(
                select(func.count(Task.id))
                .join(BoardColumn, Task.column_id == BoardColumn.id)
                .where(
                    Task.project_id == project.id,
                    BoardColumn.is_done.is_(True),
                )
            ) or 0
            mine = db.scalar(
                select(func.count(Task.id))
                .join(BoardColumn, Task.column_id == BoardColumn.id)
                .join(task_assignees, Task.id == task_assignees.c.task_id)
                .where(
                    Task.project_id == project.id,
                    task_assignees.c.user_id == user.id,
                    BoardColumn.is_done.is_(False),
                )
            ) or 0
            project_rows.append(
                {
                    "project": project,
                    "role": roles[project.id],
                    "mine_count": mine,
                    "progress": {
                        "total": total,
                        "done": done,
                        "percent": round(done / total * 100) if total else 0,
                    },
                }
            )

    return _render_page(
        request,
        "projects.html",
        settings,
        user=user,
        project_rows=project_rows,
    )


@router.post("/projects")
def create_project_form(
    db: DbSession,
    user: OptionalUser,
    name: ProjectName,
    _csrf: CsrfProtected,
    description: ProjectDescription = "",
    color: Annotated[str, Form(max_length=20)] = "blue",
) -> Response:
    if user is None:
        return _redirect("/login")
    try:
        payload = ProjectCreate(
            name=name,
            description=description.strip() or None,
            color=color if is_valid_project_color(color) else "blue",
        )
    except ValueError:
        return _redirect("/projects")

    project = Project(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        owner_id=user.id,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="owner"))
    for position, (column_name, is_done) in enumerate(DEFAULT_COLUMNS):
        db.add(
            BoardColumn(
                project_id=project.id,
                name=column_name,
                position=position,
                is_done=is_done,
            )
        )
    db.commit()
    return _redirect(f"/projects/{project.id}")


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def board_page(
    request: Request,
    project_id: int,
    db: DbSession,
    settings: AppSettings,
    user: OptionalUser,
) -> Response:
    if user is None:
        return _redirect("/login")

    project, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")

    return _render_page(
        request,
        "board.html",
        settings,
        user=user,
        **_board_context(project, membership),
    )


@router.post("/projects/{project_id}/edit")
def edit_project_form(
    project_id: int,
    db: DbSession,
    user: OptionalUser,
    name: ProjectName,
    _csrf: CsrfProtected,
    description: ProjectDescription = "",
    color: Annotated[str, Form(max_length=20)] = "blue",
) -> Response:
    if user is None:
        return _redirect("/login")
    project, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")
    if membership.role == "owner":
        project.name = name.strip()
        project.description = description.strip() or None
        if is_valid_project_color(color):
            project.color = color
        db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/members")
def add_member_form(
    project_id: int,
    db: DbSession,
    user: OptionalUser,
    phone: FormPhone,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    _, membership = _board_for(db, project_id, user)
    if membership is None or membership.role != "owner":
        return _redirect(f"/projects/{project_id}")

    try:
        normalized_phone = normalize_phone(phone)
    except ValueError:
        return _redirect(f"/projects/{project_id}")

    existing_user = db.scalar(select(User).where(User.phone == normalized_phone))
    if existing_user is None:
        invitation = db.scalar(
            select(ProjectInvitation).where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.phone == normalized_phone,
            )
        )
        if invitation is None:
            db.add(
                ProjectInvitation(
                    project_id=project_id,
                    phone=normalized_phone,
                    invited_by_id=user.id,
                )
            )
            db.commit()
        return _redirect(f"/projects/{project_id}")

    if get_membership(db, project_id, existing_user.id) is None:
        db.add(
            ProjectMember(
                project_id=project_id,
                user_id=existing_user.id,
                role="member",
            )
        )
        invitation = db.scalar(
            select(ProjectInvitation).where(
                ProjectInvitation.project_id == project_id,
                ProjectInvitation.phone == normalized_phone,
            )
        )
        if invitation is not None:
            db.delete(invitation)
        db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/members/{member_user_id}/remove")
def remove_member_form(
    project_id: int,
    member_user_id: int,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    project, membership = _board_for(db, project_id, user)
    if membership is None or membership.role != "owner":
        return _redirect(f"/projects/{project_id}")

    if member_user_id != project.owner_id:
        member = get_membership(db, project_id, member_user_id)
        if member is not None:
            db.delete(member)
            db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/invitations/{invitation_id}/cancel")
def cancel_invitation_form(
    project_id: int,
    invitation_id: int,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    _, membership = _board_for(db, project_id, user)
    if membership is None or membership.role != "owner":
        return _redirect(f"/projects/{project_id}")

    invitation = db.scalar(
        select(ProjectInvitation).where(
            ProjectInvitation.id == invitation_id,
            ProjectInvitation.project_id == project_id,
        )
    )
    if invitation is not None:
        db.delete(invitation)
        db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/columns")
def create_column_form(
    project_id: int,
    db: DbSession,
    user: OptionalUser,
    name: ColumnName,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    _, membership = _board_for(db, project_id, user)
    if membership is None or membership.role != "owner":
        return _redirect(f"/projects/{project_id}")

    try:
        payload = ColumnCreate(name=name)
    except ValueError:
        return _redirect(f"/projects/{project_id}")

    max_position = db.scalar(
        select(func.max(BoardColumn.position)).where(
            BoardColumn.project_id == project_id
        )
    )
    db.add(
        BoardColumn(
            project_id=project_id,
            name=payload.name,
            position=0 if max_position is None else int(max_position) + 1,
        )
    )
    db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/columns/{column_id}/edit")
def edit_column_form(
    project_id: int,
    column_id: int,
    db: DbSession,
    user: OptionalUser,
    name: ColumnName,
    _csrf: CsrfProtected,
    is_done: Annotated[str | None, Form()] = None,
) -> Response:
    if user is None:
        return _redirect("/login")
    _, membership = _board_for(db, project_id, user)
    if membership is None or membership.role != "owner":
        return _redirect(f"/projects/{project_id}")

    column = get_column(db, project_id, column_id)
    column.name = name.strip()
    column.is_done = is_done == "on"
    db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/columns/{column_id}/delete")
def delete_column_form(
    project_id: int,
    column_id: int,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    _, membership = _board_for(db, project_id, user)
    if membership is None or membership.role != "owner":
        return _redirect(f"/projects/{project_id}")

    column = get_column(db, project_id, column_id)
    card_count = db.scalar(
        select(func.count(Task.id)).where(Task.column_id == column_id)
    )
    column_count = db.scalar(
        select(func.count(BoardColumn.id)).where(
            BoardColumn.project_id == project_id
        )
    )
    if not card_count and column_count and column_count > 1:
        db.delete(column)
        db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/cards")
def create_card_form(
    project_id: int,
    db: DbSession,
    user: OptionalUser,
    settings: AppSettings,
    title: CardTitle,
    _csrf: CsrfProtected,
    column_id: Annotated[int | None, Form()] = None,
    description: CardDescription = "",
    due_date: Annotated[str | None, Form()] = None,
    due_in_days: Annotated[int | None, Form()] = None,
    priority: Annotated[str, Form(max_length=10)] = "normal",
    assignee_ids: Annotated[list[int], Form()] = [],
) -> Response:
    if user is None:
        return _redirect("/login")
    project, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")

    assignee_ids = assignee_ids or [user.id]

    if column_id is None:
        column = db.scalar(
            select(BoardColumn)
            .where(BoardColumn.project_id == project_id)
            .order_by(BoardColumn.position)
            .limit(1)
        )
    else:
        column = get_column(db, project_id, column_id)
    if column is None:
        return _redirect(f"/projects/{project_id}")

    due_value = _parse_due_date(due_date)
    card = Task(
        project_id=project.id,
        column_id=column.id,
        title=title.strip(),
        description=description.strip() or None,
        priority=priority if priority in PRIORITY_LABELS else "normal",
        due_date=resolve_due_date(
            due_value, None if due_value is not None else due_in_days
        ),
        position=next_position(db, column.id),
        created_by_id=user.id,
        assignees=ensure_project_members(db, project_id, assignee_ids),
        completed_at=utc_now() if column.is_done else None,
    )
    db.add(card)
    db.commit()
    notify_new_task(db, card, settings)
    return _redirect(f"/projects/{project_id}")


@router.get("/projects/{project_id}/cards/{card_id}", response_class=HTMLResponse)
def card_page(
    request: Request,
    project_id: int,
    card_id: int,
    db: DbSession,
    settings: AppSettings,
    user: OptionalUser,
) -> Response:
    if user is None:
        return _redirect("/login")
    project, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")

    card = get_task(db, project_id, card_id)
    return _render_page(
        request,
        "card.html",
        settings,
        user=user,
        card=card,
        can_delete=can_delete_card(card, membership),
        **_board_context(project, membership),
    )


@router.post("/projects/{project_id}/cards/{card_id}/edit")
def edit_card_form(
    project_id: int,
    card_id: int,
    db: DbSession,
    user: OptionalUser,
    title: CardTitle,
    column_id: Annotated[int, Form()],
    _csrf: CsrfProtected,
    description: CardDescription = "",
    assignee_ids: Annotated[list[int], Form()] = [],
    priority: Annotated[str, Form(max_length=10)] = "normal",
    due_date: Annotated[str | None, Form()] = None,
    due_in_days: Annotated[int | None, Form()] = None,
    clear_due: Annotated[str | None, Form()] = None,
    next: Annotated[str | None, Form()] = None,
) -> Response:
    if user is None:
        return _redirect("/login")
    project, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")

    card = get_task(db, project_id, card_id)
    card.title = title.strip()
    card.description = description.strip() or None
    if priority in PRIORITY_LABELS:
        card.priority = priority
    if column_id != card.column_id:
        target = get_column(db, project_id, column_id)
        move_task(db, card, target, 0)
    if assignee_ids:
        card.assignees = ensure_project_members(db, project_id, assignee_ids)

    if clear_due == "on":
        card.due_date = None
    else:
        due_value = _parse_due_date(due_date)
        if due_value is not None:
            card.due_date = due_value
        elif due_in_days is not None:
            card.due_date = resolve_due_date(None, due_in_days)

    db.commit()
    destination = f"/projects/{project_id}/cards/{card_id}"
    if next and next.startswith("/") and not next.startswith("//"):
        destination = next
    return _redirect(destination)


@router.post("/projects/{project_id}/cards/{card_id}/delete")
def delete_card_form(
    project_id: int,
    card_id: int,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfProtected,
) -> Response:
    if user is None:
        return _redirect("/login")
    _, membership = _board_for(db, project_id, user)
    if membership is None:
        return _redirect("/projects")

    card = get_task(db, project_id, card_id)
    if not can_delete_card(card, membership):
        return _redirect(f"/projects/{project_id}/cards/{card_id}")
    db.delete(card)
    db.commit()
    return _redirect(f"/projects/{project_id}")


@router.post("/projects/{project_id}/cards/{card_id}/move")
def move_card_json(
    project_id: int,
    card_id: int,
    payload: CardMove,
    db: DbSession,
    user: OptionalUser,
    _csrf: CsrfHeaderProtected,
) -> JSONResponse:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    _, membership = _board_for(db, project_id, user)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    card = get_task(db, project_id, card_id)
    target_column = get_column(db, project_id, payload.column_id)
    move_task(db, card, target_column, payload.position)
    return JSONResponse({"ok": True})
