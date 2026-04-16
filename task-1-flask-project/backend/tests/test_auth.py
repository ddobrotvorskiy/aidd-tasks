from __future__ import annotations


def test_register_success(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "alice@example.com",
            "password": "securepass",
            "full_name": "Alice Smith",
            "job_title": "Engineer",
            "department": "R&D",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["email"] == "alice@example.com"
    assert data["full_name"] == "Alice Smith"
    assert "password_hash" not in data


def test_register_duplicate_email(client, registered_user):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": registered_user["email"],
            "password": "anotherpass",
            "full_name": "Another User",
        },
    )
    assert resp.status_code == 409


def test_register_invalid_email(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "pass1234", "full_name": "Bad"},
    )
    assert resp.status_code == 422


def test_register_short_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "abc", "full_name": "Short"},
    )
    assert resp.status_code == 422


def test_login_success(client, registered_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, registered_user):
    resp = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401
