import pytest
from fastapi.testclient import TestClient

from task_manager.app import create_app
from task_manager.config import Settings

TEST_SECRET = "test-secret-key-" + "x" * 48
DEFAULT_PASSWORD = "password123"


def api_register(
    client,
    phone="09120000001",
    full_name="Test User",
    password=DEFAULT_PASSWORD,
):
    return client.post(
        "/api/auth/register",
        json={"full_name": full_name, "phone": phone, "password": password},
    )


def api_login(client, phone="09120000001", password=DEFAULT_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"phone": phone, "password": password},
    )


def auth_headers(client, phone="09120000001", password=DEFAULT_PASSWORD):
    response = api_login(client, phone, password)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_project(client, headers, name="Test Project", description=None, color=None):
    payload = {"name": name, "description": description}
    if color is not None:
        payload["color"] = color
    response = client.post(
        "/api/projects",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        jwt_secret_key=TEST_SECRET,
        access_token_expire_minutes=5,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def registered_user(client):
    response = api_register(client)
    assert response.status_code == 201, response.text
    return {"phone": "09120000001", "password": DEFAULT_PASSWORD}


@pytest.fixture()
def headers(client, registered_user):
    return auth_headers(client, registered_user["phone"])


@pytest.fixture()
def project(client, headers):
    return create_project(client, headers, name="Company Project")
