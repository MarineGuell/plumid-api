# api/tests/routes/test_auth.py
from fastapi.testclient import TestClient


def test_register_user_success(client: TestClient):
    response = client.post(
        "/auth/register",
        json={"mail": "newuser@example.com",
              "username": "newuser", "password": "Password123!"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mail"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "idusers" in data


def test_register_duplicate_email(client: TestClient):
    # Try again with same email
    response = client.post(
        "/auth/register",
        json={"mail": "newuser@example.com",
              "username": "anotheruser", "password": "Password123!"}
    )
    assert response.status_code == 400


def test_login_user_success(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"mail": "newuser@example.com", "password": "Password123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"mail": "newuser@example.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401


def test_get_me(client: TestClient):
    # Login to get token
    login_resp = client.post(
        "/auth/login",
        json={"mail": "newuser@example.com", "password": "Password123!"}
    )
    token = login_resp.json()["access_token"]

    # Get me
    me_resp = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["mail"] == "newuser@example.com"
