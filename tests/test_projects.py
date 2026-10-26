from datetime import date, timedelta

from task_manager.jalali import format_jalali
from tests.conftest import (
    api_register,
    auth_headers,
    create_project,
)


def add_member(client, headers, project_id, phone):
    return client.post(
        f"/api/projects/{project_id}/members",
        json={"phone": phone},
        headers=headers,
    )


def board(client, headers, project_id):
    response = client.get(f"/api/projects/{project_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def create_card(client, headers, project_id, title, column_id, assignee_ids=None):
    return client.post(
        f"/api/projects/{project_id}/cards",
        json={
            "title": title,
            "column_id": column_id,
            "assignee_ids": assignee_ids or [],
        },
        headers=headers,
    )


def test_create_and_list_projects(client, headers):
    project = create_project(client, headers, name="Alpha", description="desc")

    assert project["name"] == "Alpha"
    assert project["description"] == "desc"
    assert project["color"] == "blue"
    assert project["role"] == "owner"
    assert [column["name"] for column in project["columns"]] == [
        "برای انجام",
        "در حال انجام",
        "انجام‌شده",
    ]
    assert project["columns"][2]["is_done"] is True

    listing = client.get("/api/projects", headers=headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [project["id"]]
    assert listing.json()[0]["card_count"] == 0
    assert listing.json()[0]["done_count"] == 0
    assert listing.json()[0]["progress_percent"] == 0


def test_non_member_cannot_access_project(client, headers):
    project = create_project(client, headers)
    api_register(client, phone="09120000009", full_name="Outsider")
    outsider = auth_headers(client, phone="09120000009")

    assert client.get(f"/api/projects/{project['id']}", headers=outsider).status_code == 404
    assert client.get("/api/projects", headers=outsider).json() == []
    assert (
        create_card(
            client, outsider, project["id"], "Nope", project["columns"][0]["id"]
        ).status_code
        == 404
    )


def test_add_existing_user_as_member(client, headers):
    project = create_project(client, headers)
    api_register(client, phone="09120000002", full_name="Member User")

    response = add_member(client, headers, project["id"], "09120000002")
    assert response.status_code == 201
    assert response.json()["status"] == "member"

    member_headers = auth_headers(client, phone="09120000002")
    data = board(client, member_headers, project["id"])
    assert len(data["members"]) == 2

    created = create_card(
        client, member_headers, project["id"], "Member card", data["columns"][0]["id"]
    )
    assert created.status_code == 201

    duplicate = add_member(client, headers, project["id"], "09120000002")
    assert duplicate.status_code == 409


def test_invitation_is_accepted_after_registration(client, headers):
    project = create_project(client, headers)

    invited = add_member(client, headers, project["id"], "09120000003")
    assert invited.status_code == 201
    assert invited.json()["status"] == "invited"

    data = board(client, headers, project["id"])
    assert data["invitations"][0]["phone"] == "+989120000003"

    api_register(client, phone="09120000003", full_name="Invited User")
    new_member_headers = auth_headers(client, phone="09120000003")

    data = board(client, headers, project["id"])
    assert data["invitations"] == []
    assert len(data["members"]) == 2
    assert client.get(
        f"/api/projects/{project['id']}", headers=new_member_headers
    ).status_code == 200


def test_member_permissions(client, headers):
    project = create_project(client, headers)
    api_register(client, phone="09120000002", full_name="Member User")
    add_member(client, headers, project["id"], "09120000002")
    member_headers = auth_headers(client, phone="09120000002")

    assert (
        client.post(
            f"/api/projects/{project['id']}/members",
            json={"phone": "09120000004"},
            headers=member_headers,
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/projects/{project['id']}",
            json={"name": "Hacked"},
            headers=member_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/projects/{project['id']}", headers=member_headers
        ).status_code
        == 403
    )

    removed = client.delete(
        f"/api/projects/{project['id']}/members/2", headers=headers
    )
    assert removed.status_code == 204
    assert (
        client.get(f"/api/projects/{project['id']}", headers=member_headers).status_code
        == 404
    )


def test_assignees_must_be_project_members(client, headers):
    project = create_project(client, headers)
    api_register(client, phone="09120000009", full_name="Outsider")
    outsider = auth_headers(client, phone="09120000009")
    outsider_id = client.get("/api/auth/me", headers=outsider).json()["id"]

    response = create_card(
        client,
        headers,
        project["id"],
        "Card",
        project["columns"][0]["id"],
        assignee_ids=[outsider_id],
    )
    assert response.status_code == 400


def test_card_assignees_and_update(client, headers):
    project = create_project(client, headers)
    api_register(client, phone="09120000002", full_name="Member User")
    add_member(client, headers, project["id"], "09120000002")
    member_headers = auth_headers(client, phone="09120000002")
    member_id = client.get("/api/auth/me", headers=member_headers).json()["id"]

    card = create_card(
        client,
        headers,
        project["id"],
        "Assigned card",
        project["columns"][0]["id"],
        assignee_ids=[member_id],
    )
    assert card.status_code == 201
    card_id = card.json()["id"]
    assert [user["id"] for user in card.json()["assignees"]] == [member_id]

    updated = client.patch(
        f"/api/projects/{project['id']}/cards/{card_id}",
        json={"title": "Renamed card"},
        headers=member_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Renamed card"
    assert [user["id"] for user in updated.json()["assignees"]] == [member_id]

    rejected = client.patch(
        f"/api/projects/{project['id']}/cards/{card_id}",
        json={"assignee_ids": []},
        headers=member_headers,
    )
    assert rejected.status_code == 400

    assigned = client.put(
        f"/api/projects/{project['id']}/cards/{card_id}/assignees",
        json={"user_ids": [member_id]},
        headers=headers,
    )
    assert assigned.status_code == 200
    assert len(assigned.json()["assignees"]) == 1


def test_move_card_between_columns(client, headers):
    project = create_project(client, headers)
    columns = project["columns"]
    first = create_card(client, headers, project["id"], "First", columns[0]["id"]).json()
    second = create_card(client, headers, project["id"], "Second", columns[0]["id"]).json()

    data = board(client, headers, project["id"])
    assert [card["id"] for card in data["columns"][0]["cards"]] == [
        first["id"],
        second["id"],
    ]

    moved = client.post(
        f"/api/projects/{project['id']}/cards/{first['id']}/move",
        json={"column_id": columns[1]["id"], "position": 0},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["column_id"] == columns[1]["id"]

    data = board(client, headers, project["id"])
    assert [card["id"] for card in data["columns"][0]["cards"]] == [second["id"]]
    assert [card["id"] for card in data["columns"][1]["cards"]] == [first["id"]]

    client.post(
        f"/api/projects/{project['id']}/cards/{second['id']}/move",
        json={"column_id": columns[1]["id"], "position": 0},
        headers=headers,
    )
    data = board(client, headers, project["id"])
    assert [card["id"] for card in data["columns"][1]["cards"]] == [
        second["id"],
        first["id"],
    ]


def test_column_management(client, headers):
    project = create_project(client, headers)

    created = client.post(
        f"/api/projects/{project['id']}/columns",
        json={"name": "Review", "is_done": False},
        headers=headers,
    )
    assert created.status_code == 201
    column_id = created.json()["id"]

    renamed = client.patch(
        f"/api/projects/{project['id']}/columns/{column_id}",
        json={"name": "Code Review", "is_done": True},
        headers=headers,
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Code Review"
    assert renamed.json()["is_done"] is True

    card = create_card(client, headers, project["id"], "Card", column_id)
    assert card.status_code == 201
    blocked = client.delete(
        f"/api/projects/{project['id']}/columns/{column_id}", headers=headers
    )
    assert blocked.status_code == 409

    client.delete(
        f"/api/projects/{project['id']}/cards/{card.json()['id']}", headers=headers
    )
    assert (
        client.delete(
            f"/api/projects/{project['id']}/columns/{column_id}", headers=headers
        ).status_code
        == 204
    )

    remaining = board(client, headers, project["id"])
    for column in remaining["columns"][1:]:
        client.delete(
            f"/api/projects/{project['id']}/columns/{column['id']}", headers=headers
        )
    last_column = board(client, headers, project["id"])["columns"][0]
    assert (
        client.delete(
            f"/api/projects/{project['id']}/columns/{last_column['id']}",
            headers=headers,
        ).status_code
        == 400
    )


def test_project_progress(client, headers):
    project = create_project(client, headers)
    columns = project["columns"]
    create_card(client, headers, project["id"], "One", columns[0]["id"])
    second = create_card(client, headers, project["id"], "Two", columns[0]["id"]).json()

    client.post(
        f"/api/projects/{project['id']}/cards/{second['id']}/move",
        json={"column_id": columns[2]["id"], "position": 0},
        headers=headers,
    )

    summary = client.get("/api/projects", headers=headers).json()[0]
    assert summary["card_count"] == 2
    assert summary["done_count"] == 1
    assert summary["progress_percent"] == 50

    board = client.get(
        f"/api/projects/{project['id']}", headers=headers
    ).json()
    done_column = next(column for column in board["columns"] if column["is_done"])
    assert len(done_column["cards"]) == 1


def test_project_color_and_validation(client, headers):
    project = create_project(client, headers, name="Colored", color="teal")
    assert project["color"] == "teal"

    board = client.get(f"/api/projects/{project['id']}", headers=headers).json()
    assert board["color"] == "teal"

    invalid = client.post(
        "/api/projects",
        json={"name": "Bad", "color": "pink"},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_card_defaults_to_creator_as_assignee(client, headers):
    project = create_project(client, headers)
    me = client.get("/api/auth/me", headers=headers).json()["id"]

    card = client.post(
        f"/api/projects/{project['id']}/cards",
        json={"title": "Mine", "column_id": project["columns"][0]["id"]},
        headers=headers,
    )

    assert card.status_code == 201
    assert [user["id"] for user in card.json()["assignees"]] == [me]
    assert card.json()["created_by"]["id"] == me


def test_priority_and_my_tasks(client, headers):
    project = create_project(client, headers)
    column_id = project["columns"][0]["id"]
    me = client.get("/api/auth/me", headers=headers).json()["id"]

    def make(title, priority, due_in_days=None):
        payload = {
            "title": title,
            "column_id": column_id,
            "priority": priority,
            "assignee_ids": [me],
        }
        if due_in_days is not None:
            payload["due_in_days"] = due_in_days
        response = client.post(
            f"/api/projects/{project['id']}/cards",
            json=payload,
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    make("Low task", "low", 10)
    make("Urgent task", "urgent", 5)
    make("High task", "high", 1)

    tasks = client.get("/api/my/tasks", headers=headers).json()
    assert [task["title"] for task in tasks] == [
        "Urgent task",
        "High task",
        "Low task",
    ]
    assert tasks[0]["priority"] == "urgent"
    assert tasks[0]["project_color"] == "blue"
    assert tasks[0]["due_date_jalali"]

    only_open = client.get(
        "/api/my/tasks?include_done=false", headers=headers
    ).json()
    assert len(only_open) == 3


def test_assigned_to_me_count(client, headers):
    project = create_project(client, headers)
    column_id = project["columns"][0]["id"]
    me = client.get("/api/auth/me", headers=headers).json()["id"]

    card = client.post(
        f"/api/projects/{project['id']}/cards",
        json={"title": "Mine", "column_id": column_id, "assignee_ids": [me]},
        headers=headers,
    ).json()

    summary = client.get("/api/projects", headers=headers).json()[0]
    assert summary["assigned_to_me_count"] == 1

    client.post(
        f"/api/projects/{project['id']}/cards/{card['id']}/move",
        json={"column_id": project["columns"][2]["id"], "position": 0},
        headers=headers,
    )
    summary = client.get("/api/projects", headers=headers).json()[0]
    assert summary["assigned_to_me_count"] == 0


def test_update_and_delete_project(client, headers):
    project = create_project(client, headers)

    updated = client.patch(
        f"/api/projects/{project['id']}",
        json={"name": "Renamed", "description": "new"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"

    assert (
        client.delete(f"/api/projects/{project['id']}", headers=headers).status_code
        == 204
    )
    assert client.get(f"/api/projects/{project['id']}", headers=headers).status_code == 404


def test_card_due_date_and_days(client, headers):
    project = create_project(client, headers)
    column_id = project["columns"][0]["id"]

    explicit = client.post(
        f"/api/projects/{project['id']}/cards",
        json={"title": "Due card", "column_id": column_id, "due_date": "2030-01-02"},
        headers=headers,
    )
    assert explicit.status_code == 201
    assert explicit.json()["due_date"] == "2030-01-02"
    assert explicit.json()["due_date_jalali"] == format_jalali(date(2030, 1, 2))
    assert explicit.json()["days_remaining"] > 0

    relative = client.post(
        f"/api/projects/{project['id']}/cards",
        json={"title": "Relative card", "column_id": column_id, "due_in_days": 3},
        headers=headers,
    )
    assert relative.status_code == 201
    assert relative.json()["due_date"] == (date.today() + timedelta(days=3)).isoformat()
    card_id = relative.json()["id"]

    updated = client.patch(
        f"/api/projects/{project['id']}/cards/{card_id}",
        json={"due_in_days": 5},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["due_date"] == (date.today() + timedelta(days=5)).isoformat()

    cleared = client.patch(
        f"/api/projects/{project['id']}/cards/{card_id}",
        json={"due_date": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["due_date"] is None
    assert cleared.json()["days_remaining"] is None

    both = client.post(
        f"/api/projects/{project['id']}/cards",
        json={
            "title": "Both",
            "column_id": column_id,
            "due_date": "2030-01-02",
            "due_in_days": 1,
        },
        headers=headers,
    )
    assert both.status_code == 422


def test_only_creator_can_delete_card(client, headers):
    project = create_project(client, headers)
    api_register(client, phone="09120000002", full_name="Member User")
    add_member(client, headers, project["id"], "09120000002")
    member_headers = auth_headers(client, phone="09120000002")
    column_id = project["columns"][0]["id"]

    owner_card = create_card(
        client, headers, project["id"], "Owner card", column_id
    ).json()
    member_card = create_card(
        client, member_headers, project["id"], "Member card", column_id
    ).json()

    assert (
        client.delete(
            f"/api/projects/{project['id']}/cards/{owner_card['id']}",
            headers=member_headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/projects/{project['id']}/cards/{member_card['id']}",
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/projects/{project['id']}/cards/{owner_card['id']}",
            headers=headers,
        ).status_code
        == 204
    )
    assert (
        client.delete(
            f"/api/projects/{project['id']}/cards/{member_card['id']}",
            headers=member_headers,
        ).status_code
        == 204
    )
