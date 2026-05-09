"""
Tests for authentication endpoints.
"""

import pytest


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


class TestRegister:
    def test_register_student(self, client):
        res = client.post(
            "/api/auth/register",
            json={
                "name": "Alice",
                "email": "alice@example.com",
                "password": "password1",
                "role": "student",
            },
        )
        assert res.status_code == 201
        data = res.get_json()
        assert "token" in data
        assert data["user"]["role"] == "student"

    def test_register_missing_fields(self, client):
        res = client.post("/api/auth/register", json={"email": "x@x.com"})
        assert res.status_code == 400

    def test_register_duplicate_email(self, client):
        payload = {
            "name": "Bob",
            "email": "bob_dup@example.com",
            "password": "password1",
        }
        client.post("/api/auth/register", json=payload)
        res = client.post("/api/auth/register", json=payload)
        assert res.status_code == 409

    def test_register_short_password(self, client):
        res = client.post(
            "/api/auth/register",
            json={"name": "C", "email": "c@c.com", "password": "abc"},
        )
        assert res.status_code == 400

    def test_register_invalid_role(self, client):
        res = client.post(
            "/api/auth/register",
            json={"name": "D", "email": "d@d.com", "password": "abcdef", "role": "superuser"},
        )
        assert res.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        client.post(
            "/api/auth/register",
            json={"name": "Eve", "email": "eve@example.com", "password": "password1"},
        )
        res = client.post(
            "/api/auth/login",
            json={"email": "eve@example.com", "password": "password1"},
        )
        assert res.status_code == 200
        assert "token" in res.get_json()

    def test_login_wrong_password(self, client):
        res = client.post(
            "/api/auth/login",
            json={"email": "admin@test.local", "password": "wrong"},
        )
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        res = client.post(
            "/api/auth/login",
            json={"email": "nobody@nowhere.com", "password": "password"},
        )
        assert res.status_code == 401


class TestMe:
    def test_get_me(self, client, auth_headers_admin):
        res = client.get("/api/auth/me", headers=auth_headers_admin)
        assert res.status_code == 200
        assert res.get_json()["role"] == "admin"

    def test_get_me_no_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401


class TestUsers:
    def test_list_users_admin(self, client, auth_headers_admin):
        res = client.get("/api/auth/users", headers=auth_headers_admin)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_list_users_student_forbidden(self, client, student_user):
        _, headers = student_user
        res = client.get("/api/auth/users", headers=headers)
        assert res.status_code == 403
