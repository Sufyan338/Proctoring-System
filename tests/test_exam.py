"""
Tests for exam management endpoints.
"""

import pytest


@pytest.fixture()
def exam(client, auth_headers_admin):
    """Create a test exam and return its data."""
    res = client.post(
        "/api/exams/",
        json={"title": "Sample Exam", "description": "Test", "duration_minutes": 30},
        headers=auth_headers_admin,
    )
    assert res.status_code == 201
    return res.get_json()


class TestCreateExam:
    def test_create_exam_admin(self, client, auth_headers_admin):
        res = client.post(
            "/api/exams/",
            json={"title": "Maths Final", "duration_minutes": 90},
            headers=auth_headers_admin,
        )
        assert res.status_code == 201
        data = res.get_json()
        assert data["title"] == "Maths Final"

    def test_create_exam_no_title(self, client, auth_headers_admin):
        res = client.post("/api/exams/", json={}, headers=auth_headers_admin)
        assert res.status_code == 400

    def test_create_exam_student_forbidden(self, client, student_user):
        _, headers = student_user
        res = client.post(
            "/api/exams/",
            json={"title": "Nope"},
            headers=headers,
        )
        assert res.status_code == 403


class TestListExams:
    def test_list_exams(self, client, auth_headers_admin, exam):
        res = client.get("/api/exams/", headers=auth_headers_admin)
        assert res.status_code == 200
        assert any(e["id"] == exam["id"] for e in res.get_json())


class TestGetExam:
    def test_get_exam(self, client, auth_headers_admin, exam):
        res = client.get(f"/api/exams/{exam['id']}", headers=auth_headers_admin)
        assert res.status_code == 200
        assert res.get_json()["id"] == exam["id"]

    def test_get_nonexistent_exam(self, client, auth_headers_admin):
        res = client.get("/api/exams/99999", headers=auth_headers_admin)
        assert res.status_code == 404


class TestDeleteExam:
    def test_delete_exam(self, client, auth_headers_admin):
        create_res = client.post(
            "/api/exams/",
            json={"title": "To Delete"},
            headers=auth_headers_admin,
        )
        eid = create_res.get_json()["id"]
        del_res = client.delete(f"/api/exams/{eid}", headers=auth_headers_admin)
        assert del_res.status_code == 200


class TestSession:
    def test_start_and_end_session(self, client, student_user, exam):
        user, headers = student_user

        # Start session
        res = client.post(f"/api/exams/{exam['id']}/start", headers=headers)
        assert res.status_code in (200, 201)
        session = res.get_json()
        assert session["status"] == "active"

        sid = session["id"]

        # End session
        end_res = client.post(f"/api/exams/sessions/{sid}/end", headers=headers)
        assert end_res.status_code == 200
        assert end_res.get_json()["status"] in ("completed", "flagged")

    def test_start_session_admin_forbidden(self, client, auth_headers_admin, exam):
        res = client.post(f"/api/exams/{exam['id']}/start", headers=auth_headers_admin)
        assert res.status_code == 403

    def test_list_sessions(self, client, auth_headers_admin):
        res = client.get("/api/exams/sessions/", headers=auth_headers_admin)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)
