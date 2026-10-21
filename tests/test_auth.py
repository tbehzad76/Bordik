from datetime import UTC, datetime, timedelta

import jwt

from tests.conftest import TEST_SECRET, api_login, api_register


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_returns_safe_user_data(client):
    response = api_register(client, phone="0912 000 0001")

    assert response.status_code == 201
    data = response.json()
    assert data["phone"] == "+989120000001"
    assert data["full_name"] == "Test User"
    assert "password" not in data
    assert "hashed_password" not in data
    assert "created_at" in data


def test_duplicate_phone_is_rejected(client):
    assert api_register(client).status_code == 201
    response = api_register(client, phone="+989120000001")

    assert response.status_code == 409


def test_invalid_phone_is_rejected(client):
    response = api_register(client, phone="not-a-phone")

    assert response.status_code == 422


def test_short_password_is_rejected(client):
    response = api_register(client, password="short")

    assert response.status_code == 422


def test_login_and_read_current_user(client):
    api_register(client)
    response = api_login(client, phone="+98 912 000 0001")

    assert response.status_code == 200
    token_data = response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["phone"] == "+989120000001"


def test_login_with_wrong_password_is_rejected(client):
    api_register(client)

    response = api_login(client, password="wrong-password")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_with_unknown_phone_is_rejected(client):
    response = api_login(client, phone="09129999999")

    assert response.status_code == 401


def test_oauth2_token_endpoint(client):
    api_register(client)

    response = client.post(
        "/api/auth/token",
        data={"username": "09120000001", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_protected_endpoint_requires_valid_token(client):
    api_register(client)

    missing = client.get("/api/auth/me")
    invalid = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert invalid.status_code == 401


def test_expired_token_is_rejected(client):
    api_register(client)
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "1",
            "type": "access",
            "iat": now - timedelta(minutes=10),
            "exp": now - timedelta(minutes=5),
        },
        TEST_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired}"},
    )

    assert response.status_code == 401
