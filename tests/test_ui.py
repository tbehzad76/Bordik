import re

from tests.conftest import api_register

DEFAULT_PHONE = "09120000001"
DEFAULT_PASSWORD = "password123"


def extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None, "CSRF token not found"
    return match.group(1)


def register_via_ui(
    client,
    phone=DEFAULT_PHONE,
    full_name="UI User",
    password=DEFAULT_PASSWORD,
    expect_status=303,
):
    page = client.get("/register")
    assert page.status_code == 200
    token = extract_csrf(page.text)
    response = client.post(
        "/register",
        data={
            "full_name": full_name,
            "phone": phone,
            "password": password,
            "password_confirm": password,
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code == expect_status, response.text
    return response


def login_via_ui(client, phone=DEFAULT_PHONE, password=DEFAULT_PASSWORD):
    page = client.get("/login")
    token = extract_csrf(page.text)
    response = client.post(
        "/login",
        data={"phone": phone, "password": password, "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return response


def create_project_via_ui(client, name="UI Project", description="Board"):
    page = client.get("/projects")
    token = extract_csrf(page.text)
    response = client.post(
        "/projects",
        data={"name": name, "description": description, "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].rsplit("/", 1)[-1])


def test_pages_require_login(client):
    root = client.get("/", follow_redirects=False)
    projects = client.get("/projects", follow_redirects=False)

    assert root.status_code == 303
    assert root.headers["location"] == "/login"
    assert projects.status_code == 303
    assert projects.headers["location"] == "/login"


def test_login_page_has_security_headers_and_csrf(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "شماره همراه" in response.text
    assert 'class="brand-mark"' in response.text
    assert "M18 33l9 9 19-20" in response.text
    assert "csrf_token" in response.cookies
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert "font-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_register_logs_user_in(client):
    response = register_via_ui(client)
    cookie = response.headers.get("set-cookie", "")

    assert "access_token=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie

    page = client.get("/projects")
    assert page.status_code == 200
    assert "UI User" in page.text


def test_register_validation_errors(client):
    page = client.get("/register")
    token = extract_csrf(page.text)
    mismatch = client.post(
        "/register",
        data={
            "full_name": "UI User",
            "phone": "09120000001",
            "password": "one-password",
            "password_confirm": "other-password",
            "csrf_token": token,
        },
    )
    assert mismatch.status_code == 200
    assert "یکسان نیستند" in mismatch.text

    invalid_phone = client.post(
        "/register",
        data={
            "full_name": "UI User",
            "phone": "abc",
            "password": DEFAULT_PASSWORD,
            "password_confirm": DEFAULT_PASSWORD,
            "csrf_token": token,
        },
    )
    assert invalid_phone.status_code == 200
    assert "معتبر نیست" in invalid_phone.text

    register_via_ui(client)
    duplicate = register_via_ui(client, expect_status=200)
    assert "از قبل وجود دارد" in duplicate.text


def test_login_success_and_generic_error(client):
    register_via_ui(client)
    token = extract_csrf(client.get("/projects").text)
    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)

    page = client.get("/login")
    token = extract_csrf(page.text)
    wrong = client.post(
        "/login",
        data={
            "phone": DEFAULT_PHONE,
            "password": "wrong-password",
            "csrf_token": token,
        },
    )
    assert wrong.status_code == 200
    assert "نادرست است" in wrong.text

    token = extract_csrf(wrong.text)
    good = client.post(
        "/login",
        data={
            "phone": DEFAULT_PHONE,
            "password": DEFAULT_PASSWORD,
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert good.status_code == 303
    assert good.headers["location"] == "/projects"


def test_csrf_token_is_required(client):
    page = client.get("/login")
    extract_csrf(page.text)
    rejected = client.post(
        "/login",
        data={
            "phone": DEFAULT_PHONE,
            "password": DEFAULT_PASSWORD,
            "csrf_token": "invalid-token",
        },
    )
    assert rejected.status_code == 403


def test_project_board_flow(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client, name="Company Board")

    board = client.get(f"/projects/{project_id}")
    assert board.status_code == 200
    assert "Company Board" in board.text
    assert board.text.count('class="board-column"') == 3
    assert board.text.index("project-color-strip") < board.text.index("board-head")

    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    created = client.post(
        f"/projects/{project_id}/cards",
        data={
            "title": "First board card",
            "description": "Some details",
            "column_id": str(column_id),
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    board = client.get(f"/projects/{project_id}")
    assert "First board card" in board.text
    card_id = int(re.search(r'data-card-id="(\d+)"', board.text).group(1))

    card_page = client.get(f"/projects/{project_id}/cards/{card_id}")
    assert card_page.status_code == 200
    assert "First board card" in card_page.text

    edited = client.post(
        f"/projects/{project_id}/cards/{card_id}/edit",
        data={
            "title": "Edited card",
            "description": "Updated",
            "column_id": str(column_id),
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert edited.status_code == 303
    assert "Edited card" in client.get(f"/projects/{project_id}").text


def test_add_member_and_invitation_via_ui(client):
    register_via_ui(client, phone="09120000001", full_name="Owner User")
    project_id = create_project_via_ui(client)
    api_register(client, phone="09120000002", full_name="Member User")

    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    added = client.post(
        f"/projects/{project_id}/members",
        data={"phone": "09120000002", "csrf_token": token},
        follow_redirects=False,
    )
    assert added.status_code == 303
    assert "Member User" in client.get(f"/projects/{project_id}").text

    invited = client.post(
        f"/projects/{project_id}/members",
        data={"phone": "09120000003", "csrf_token": token},
        follow_redirects=False,
    )
    assert invited.status_code == 303
    assert "+989120000003" in client.get(f"/projects/{project_id}").text

    api_register(client, phone="09120000003", full_name="Invited User")
    assert "Invited User" in client.get(f"/projects/{project_id}").text


def test_member_can_open_board_but_outsider_cannot(client):
    register_via_ui(client, phone="09120000001", full_name="Owner User")
    project_id = create_project_via_ui(client)
    api_register(client, phone="09120000002", full_name="Member User")
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    client.post(
        f"/projects/{project_id}/members",
        data={"phone": "09120000002", "csrf_token": token},
        follow_redirects=False,
    )

    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    register_via_ui(client, phone="09120000002", full_name="Member User", expect_status=200)
    token = extract_csrf(client.get("/login").text)
    client.post(
        "/login",
        data={
            "phone": "09120000002",
            "password": DEFAULT_PASSWORD,
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert client.get(f"/projects/{project_id}").status_code == 200

    client.post("/logout", data={"csrf_token": extract_csrf(client.get("/projects").text)}, follow_redirects=False)
    register_via_ui(client, phone="09120000009", full_name="Outsider")
    outsider = client.get(f"/projects/{project_id}", follow_redirects=False)
    assert outsider.status_code == 303
    assert outsider.headers["location"] == "/projects"


def test_drag_and_drop_move_endpoint(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    client.post(
        f"/projects/{project_id}/cards",
        data={"title": "Draggable", "column_id": str(column_id), "csrf_token": token},
        follow_redirects=False,
    )
    board = client.get(f"/projects/{project_id}")
    card_id = int(re.search(r'data-card-id="(\d+)"', board.text).group(1))
    column_ids = [int(value) for value in re.findall(r'data-column-id="(\d+)"', board.text)]

    moved = client.post(
        f"/projects/{project_id}/cards/{card_id}/move",
        json={"column_id": column_ids[-1], "position": 0},
        headers={"X-CSRF-Token": token},
    )
    assert moved.status_code == 200
    assert moved.json() == {"ok": True}

    rejected = client.post(
        f"/projects/{project_id}/cards/{card_id}/move",
        json={"column_id": column_ids[0], "position": 0},
        headers={"X-CSRF-Token": "bad-token"},
    )
    assert rejected.status_code == 403


def test_ui_isolation_between_users(client):
    register_via_ui(client, phone="09120000001", full_name="First")
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    client.post(
        f"/projects/{project_id}/cards",
        data={"title": "Private", "column_id": str(column_id), "csrf_token": token},
        follow_redirects=False,
    )
    card_id = int(re.search(r'data-card-id="(\d+)"', client.get(f"/projects/{project_id}").text).group(1))

    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    register_via_ui(client, phone="09120000002", full_name="Second")
    other_token = extract_csrf(client.get("/projects").text)
    response = client.post(
        f"/projects/{project_id}/cards/{card_id}/move",
        json={"column_id": column_id, "position": 0},
        headers={"X-CSRF-Token": other_token},
    )
    assert response.status_code == 404


def test_logout_clears_session(client):
    register_via_ui(client)
    token = extract_csrf(client.get("/projects").text)
    response = client.post("/logout", data={"csrf_token": token}, follow_redirects=False)

    assert response.status_code == 303
    assert "access_token" not in client.cookies
    assert client.get("/projects", follow_redirects=False).status_code == 303


def test_html_is_escaped(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    payload = '<script>alert("xss")</script>'
    client.post(
        f"/projects/{project_id}/cards",
        data={"title": payload, "csrf_token": token},
        follow_redirects=False,
    )
    page = client.get(f"/projects/{project_id}")

    assert payload not in page.text
    assert "&lt;script&gt;" in page.text


def test_api_does_not_accept_ui_cookie(client):
    register_via_ui(client)

    assert client.get("/api/projects").status_code == 401


def test_project_modal_and_progress(client):
    register_via_ui(client)
    projects_page = client.get("/projects")
    assert 'data-open-project-modal' in projects_page.text
    assert "<dialog" in projects_page.text
    assert "projects.js" in projects_page.text

    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    assert "progress" in board.text

    projects_page = client.get("/projects")
    assert "وظیفه انجام شده" in projects_page.text


def test_board_card_modal_priority_and_my_tasks(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")

    assert 'id="card-modal"' in board.text
    assert 'name="priority"' in board.text
    assert 'name="assignee_ids"' in board.text
    assert "data-add-card" in board.text
    assert "jalalidatepicker.min.js" in board.text
    assert "data-require-assignee" in board.text
    assert "assignee-check.js" in board.text
    assert "?v=" in board.text
    assert re.search(r'name="assignee_ids" value="\d+"[^>]*required', board.text) is None

    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    assignee_id = int(re.search(r'name="assignee_ids" value="(\d+)"', board.text).group(1))

    created = client.post(
        f"/projects/{project_id}/cards",
        data={
            "title": "Urgent board card",
            "column_id": str(column_id),
            "priority": "urgent",
            "assignee_ids": str(assignee_id),
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    board = client.get(f"/projects/{project_id}")
    assert "priority-urgent" in board.text

    my_tasks = client.get("/my-tasks")
    assert my_tasks.status_code == 200
    assert "Urgent board card" in my_tasks.text
    assert "وظایف من" in my_tasks.text
    assert my_tasks.text.count('class="tab ') == 2
    assert "data-auto-submit" in my_tasks.text
    assert "switch-box" in my_tasks.text


def test_project_color_edit_and_mine_tag(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    assert 'name="color"' in board.text

    token = extract_csrf(board.text)
    edited = client.post(
        f"/projects/{project_id}/edit",
        data={
            "name": "Recolored",
            "description": "",
            "color": "rose",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert edited.status_code == 303
    board = client.get(f"/projects/{project_id}")
    assert "color-rose" in board.text

    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    assignee_id = int(
        re.search(r'name="assignee_ids" value="(\d+)"', board.text).group(1)
    )
    created = client.post(
        f"/projects/{project_id}/cards",
        data={
            "title": "Assigned to me",
            "column_id": str(column_id),
            "assignee_ids": str(assignee_id),
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    projects_page = client.get("/projects")
    assert "وظیفه برای شما" in projects_page.text
    assert "badge-mine" in projects_page.text
    assert "project-card-badges" in projects_page.text
    assert "project-card color-rose" in projects_page.text


def test_my_tasks_done_filter(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    columns = list(dict.fromkeys(re.findall(r'data-column-id="(\d+)"', board.text)))
    assignee_id = int(
        re.search(r'name="assignee_ids" value="(\d+)"', board.text).group(1)
    )
    created = client.post(
        f"/projects/{project_id}/cards",
        data={
            "title": "Done card",
            "column_id": columns[0],
            "assignee_ids": str(assignee_id),
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    card_id = int(
        re.search(r'data-card-id="(\d+)"', client.get(f"/projects/{project_id}").text).group(1)
    )
    moved = client.post(
        f"/projects/{project_id}/cards/{card_id}/move",
        json={"column_id": int(columns[2]), "position": 0},
        headers={"X-CSRF-Token": token},
    )
    assert moved.status_code == 200

    default_page = client.get("/my-tasks")
    assert "Done card" not in default_page.text
    assert 'name="include_done" value="0"' in default_page.text

    with_done = client.get("/my-tasks?include_done=1")
    assert "Done card" in with_done.text
    assert 'name="include_done" value="1"' in with_done.text


def test_browser_notification_feed(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    assert "notif-panel" in board.text
    assert "notifications.js" in board.text
    assert "notif-hint" in board.text

    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    assignee_id = int(
        re.search(r'name="assignee_ids" value="(\d+)"', board.text).group(1)
    )
    created = client.post(
        f"/projects/{project_id}/cards",
        data={
            "title": "Notify me",
            "column_id": str(column_id),
            "assignee_ids": str(assignee_id),
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert created.status_code == 303

    feed = client.get("/ui/notifications/feed")
    assert feed.status_code == 200
    data = feed.json()
    assert data["unread"] == 1
    assert "Notify me" in data["items"][0]["title"]

    read = client.post(
        "/ui/notifications/read",
        json={"all": True},
        headers={"X-CSRF-Token": token},
    )
    assert read.status_code == 200
    assert client.get("/ui/notifications/feed").json()["unread"] == 0


def test_owner_can_delete_project_via_ui(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client, name="Delete me")
    board = client.get(f"/projects/{project_id}")
    assert f"/projects/{project_id}/delete" in board.text
    assert "data-confirm" in board.text
    assert 'id="project-settings-modal"' in board.text
    assert "data-open-project-settings" in board.text

    token = extract_csrf(board.text)
    response = client.post(
        f"/projects/{project_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/projects"
    assert "Delete me" not in client.get("/projects").text


def test_static_assets_are_served(client):
    css = client.get("/static/style.css")
    js = client.get("/static/board.js")
    picker_js = client.get("/static/vendor/jalalidatepicker/jalalidatepicker.min.js")
    picker_css = client.get("/static/vendor/jalalidatepicker/jalalidatepicker.min.css")
    picker_init = client.get("/static/jalali-init.js")
    confirm_js = client.get("/static/confirm-submit.js")
    font = client.get("/static/fonts/Vazirmatn-Regular.ttf")

    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert "Vazirmatn" in css.text
    assert "overflow-x: auto" not in css.text.split(".board {")[1].split("}")[0]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
    assert picker_js.status_code == 200
    assert picker_css.status_code == 200
    assert picker_init.status_code == 200
    assert "jalaliDatepicker" in picker_init.text
    assert confirm_js.status_code == 200
    assert "confirm-submit" not in confirm_js.text or "window.confirm" in confirm_js.text
    assert "place-items: center" in css.text
    assert font.status_code == 200
    assert len(font.content) > 1000


def test_card_due_date_via_ui(client):
    register_via_ui(client)
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))

    created = client.post(
        f"/projects/{project_id}/cards",
        data={
            "title": "Timed card",
            "column_id": str(column_id),
            "due_in_days": "4",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    assert "روز مانده" in client.get(f"/projects/{project_id}").text

    card_id = int(
        re.search(
            r'data-card-id="(\d+)"', client.get(f"/projects/{project_id}").text
        ).group(1)
    )
    card = client.get(f"/projects/{project_id}/cards/{card_id}")
    assert 'name="due_date"' in card.text
    assert 'name="due_in_days"' in card.text
    assert "data-jdp" in card.text
    assert "jalalidatepicker.min.js" in card.text

    edited = client.post(
        f"/projects/{project_id}/cards/{card_id}/edit",
        data={
            "title": "Timed card",
            "column_id": str(column_id),
            "due_date": "1409/02/12",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert edited.status_code == 303
    assert "1409/02/12" in client.get(
        f"/projects/{project_id}/cards/{card_id}"
    ).text


def test_only_creator_can_delete_via_ui(client):
    register_via_ui(client, phone="09120000001", full_name="Owner User")
    project_id = create_project_via_ui(client)
    board = client.get(f"/projects/{project_id}")
    token = extract_csrf(board.text)
    column_id = int(re.search(r'data-column-id="(\d+)"', board.text).group(1))
    client.post(
        f"/projects/{project_id}/cards",
        data={"title": "Owner card", "column_id": str(column_id), "csrf_token": token},
        follow_redirects=False,
    )
    card_id = int(
        re.search(
            r'data-card-id="(\d+)"', client.get(f"/projects/{project_id}").text
        ).group(1)
    )

    api_register(client, phone="09120000002", full_name="Member User")
    client.post(
        f"/projects/{project_id}/members",
        data={"phone": "09120000002", "csrf_token": token},
        follow_redirects=False,
    )

    client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    login_via_ui(client, phone="09120000002")
    member_token = extract_csrf(client.get(f"/projects/{project_id}").text)

    card_page = client.get(f"/projects/{project_id}/cards/{card_id}")
    assert card_page.status_code == 200
    assert "فقط سازنده" in card_page.text

    attempt = client.post(
        f"/projects/{project_id}/cards/{card_id}/delete",
        data={"csrf_token": member_token},
        follow_redirects=False,
    )
    assert attempt.status_code == 303
    assert (
        client.get(f"/projects/{project_id}/cards/{card_id}").status_code == 200
    )
