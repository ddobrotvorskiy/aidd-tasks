from __future__ import annotations

import pytest

from app import create_app, db as _db


@pytest.fixture(scope="session")
def app():
    """Create application for testing with an in-memory SQLite database."""
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret",
        "SECRET_KEY": "test-secret",
        "UPLOAD_FOLDER": "/tmp/test_uploads",
        "WTF_CSRF_ENABLED": False,
    }
    application = create_app(config_override=test_config)

    with application.app_context():
        _db.create_all()
        yield application
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()


@pytest.fixture()
def registered_user(client):
    """Register and return a test user."""
    payload = {
        "email": "test@example.com",
        "password": "password123",
        "full_name": "Test User",
        "job_title": "Developer",
        "department": "Engineering",
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    return payload


@pytest.fixture()
def auth_headers(client, registered_user):
    """Return Authorization headers for a logged-in test user."""
    resp = client.post(
        "/api/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
