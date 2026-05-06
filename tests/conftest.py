"""
Pytest fixtures shared across all test modules.
"""

import uuid

import pytest

from backend.app import create_app
from backend.models import db as _db


@pytest.fixture(scope="session")
def app():
    """Create application with in-memory SQLite database for tests."""
    application = create_app("development")
    application.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        JWT_SECRET_KEY="test-jwt-secret",
        SECRET_KEY="test-secret",
        ADMIN_EMAIL="admin@test.local",
        ADMIN_PASSWORD="Test@12345",
    )

    with application.app_context():
        _db.create_all()
        # Seed admin
        from backend.models import User
        if not User.query.filter_by(email="admin@test.local").first():
            admin = User(name="Test Admin", email="admin@test.local", role="admin")
            admin.set_password("Test@12345")
            _db.session.add(admin)
            _db.session.commit()

        yield application

        _db.drop_all()


@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture()
def auth_headers_admin(client):
    """Return JWT auth headers for the default admin user."""
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "Test@12345"},
    )
    token = res.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student_user(client):
    """Register a unique student per test and return (user_dict, auth_headers)."""
    unique_email = f"student_{uuid.uuid4().hex[:8]}@test.local"
    res = client.post(
        "/api/auth/register",
        json={
            "name": "Test Student",
            "email": unique_email,
            "password": "Student@1",
            "role": "student",
        },
    )
    data = res.get_json()
    assert "token" in data, f"Registration failed: {data}"
    token = data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return data["user"], headers
